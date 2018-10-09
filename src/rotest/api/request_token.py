# pylint: disable=unused-argument, no-self-use
from __future__ import absolute_import
from builtins import str
import uuid
import six.moves.http_client

from swaggapi.api.builder.server.response import Response
from swaggapi.api.builder.server.request import DjangoRequestView

from rotest.api.common.models import GenericModel
from rotest.api.test_control.middleware import session_middleware, SessionData
from rotest.api.common.responses import (TokenResponseModel,
                                         FailureResponseModel)


class RequestToken(DjangoRequestView):
    """Initialize the tests run data.

    Args:
        tests_tree (dict): contains the hierarchy of the tests in the run.
        run_data (dict): contains additional data about the run.
    """
    URI = "tests/get_token"
    DEFAULT_MODEL = GenericModel
    DEFAULT_RESPONSES = {
        six.moves.http_client.OK: TokenResponseModel,
        six.moves.http_client.BAD_REQUEST: FailureResponseModel
    }
    TAGS = {
        "get": ["Token"]
    }

    @session_middleware
    def get(self, request, sessions, *args, **kwargs):
        """Initialize the tests run data.

        Args:
            tests_tree (dict): contains the hierarchy of the tests in the run.
            run_data (dict): contains additional data about the run.
        """
        session_token = str(uuid.uuid4())
        sessions[session_token] = SessionData()
        response = {
            "token": session_token
        }
        return Response(response, status=six.moves.http_client.OK)
