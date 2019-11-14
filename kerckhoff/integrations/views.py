from rest_framework.request import Request
from rest_framework.response import Response

from rest_framework.views import APIView
from rest_framework.exceptions import NotFound

from kerckhoff.integrations.models import Integration


class IntegrationOAuthView(APIView):
    def get(self, request: Request):
        package_set_slug = request.query_params.get("ps-slug")
        integration_id = request.query_params.get("id")
        code = request.query_params.get("code")
        state = request.query_params.get("state")

        if code is not None and state is not None:
            integration = Integration.objects.filter(_auth_data__state=state).first()
            if integration is None:
                raise NotFound(detail="No integration is found!")
            else:
                integration.validate(code)
                return Response({"packageset_slug": integration.package_set.slug})

        if package_set_slug is not None and integration_id is not None:
            integration = Integration.objects.filter(id=integration_id).first()
            if integration is None:
                raise NotFound(detail="No integration is found!")
            else:
                url = integration.begin_authorization()
                return Response({"redirect_url": url})
        return NotFound
