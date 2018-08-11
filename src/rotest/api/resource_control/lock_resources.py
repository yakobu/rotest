import httplib
from datetime import datetime

from django.contrib.auth import models as auth_models
from django.core.exceptions import FieldError
from django.db import transaction
from django.db.models.query_utils import Q
from swagapi.api.wrapper import RequestView, Response, BadRequest

from rotest.api.common.models import DescribedResourcesPostModel
from rotest.api.common.responses import \
    (BadRequestResponseModel, InfluencedResourcesResponseModel)
from rotest.management.common.json_parser import JSONParser
from rotest.management.common.resource_descriptor import ResourceDescriptor
from rotest.management.common.utils import get_username


class LockResources(RequestView):
    """Lock the given resources one by one.

    Note:
        If one of the resources fails to lock, all the resources
        that has
        been locked until that resource will be released.
    """
    URI = "resources/lock_resources"
    DEFAULT_MODEL = DescribedResourcesPostModel
    DEFAULT_RESPONSES = {
        httplib.OK: InfluencedResourcesResponseModel,
        httplib.BAD_REQUEST: BadRequestResponseModel
    }
    TAGS = {
        "post": ["Resources"]
    }

    def _lock_resource(self, resource, user_name):
        """Mark the resource as locked by the given user.

        For complex resource, marks also its sub-resources as locked by the
        given user.

        Note:
            The given resource *must* be available.

        Args:
            resource (ResourceData): resource to lock.
            user_name (str): name of the locking user.
        """
        for sub_resource in resource.get_sub_resources():
            self._lock_resource(sub_resource, user_name)

        resource.owner = user_name
        resource.owner_time = datetime.now()
        resource.save()

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        """Lock the given resources one by one.

        Note:
            If one of the resources fails to lock, all the resources that has
            been locked until that resource will be released.
        """
        locked_resources = []
        user_name = get_username(request)
        descriptors = request.model.descriptors

        if not auth_models.User.objects.filter(username=user_name).exists():
            raise BadRequest({
                "details": "User {} has no matching object in the "
                              "DB".format(user_name)})

        user = auth_models.User.objects.get(username=user_name)

        groups = list(user.groups.all())

        for descriptor_dict in descriptors:
            desc = ResourceDescriptor.decode(descriptor_dict)
            # query for resources that are usable and match the user's
            # preference, which are either belong to a group he's in or
            # don't belong to any group.
            query = (Q(is_usable=True, **desc.properties) &
                     (Q(group__isnull=True) | Q(group__in=groups)))
            try:
                matches = desc.type.objects.filter(query).order_by('-reserved')

            except FieldError as e:
                raise BadRequest(e.message)

            if matches.count() == 0:
                raise BadRequest({
                    "details": "No existing resource meets "
                               "the requirements: {!r}".format(desc)})

            availables = (resource for resource in matches
                          if resource.is_available(user_name))

            try:
                resource = availables.next()

                self._lock_resource(resource, user_name)
                locked_resources.append(resource)

            except StopIteration:
                raise BadRequest({
                    "details": "No available resource meets "
                               "the requirements: {!r}".format(desc)})

        encoder = JSONParser()
        response = [encoder.encode(resource)
                    for resource in locked_resources]
        return Response({
            "resource_descriptors": response
        }, status=httplib.OK)
