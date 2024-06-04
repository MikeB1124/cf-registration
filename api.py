from stacker.blueprints.base import Blueprint
from troposphere import Output, Ref, apigateway, GetAtt, ssm


class Registration(Blueprint):
    VARIABLES = {"env-dict": {"type": dict}}

    def create_api_gateway(self):
        self.api = apigateway.RestApi(
            "RegistrationApi",
            Name=self.get_variables()["env-dict"]["ApiName"],
            ApiKeySourceType="HEADER",
            EndpointConfiguration=apigateway.EndpointConfiguration(Types=["REGIONAL"]),
        )
        self.template.add_resource(self.api)

        self.registration_api_resource = apigateway.Resource(
            "RegistrationResource",
            ParentId=GetAtt(self.api, "RootResourceId"),
            RestApiId=Ref(self.api),
            PathPart="registration",
        )
        self.template.add_resource(self.registration_api_resource)

        self.template.add_output(
            Output(
                "RegestrationApiId",
                Value=Ref(self.api),
            )
        )

    def store_ssm_parameters(self):
        ssm_api_id = ssm.Parameter(
            "RegistrationApiId",
            Name="/registration/api/id",
            Type="String",
            Value=Ref(self.api),
        )
        self.template.add_resource(ssm_api_id)

        ssm_api_parent_resource_id = ssm.Parameter(
            "RegistrationApiParentResourceId",
            Name="/registration/api/parent/resource/id",
            Type="String",
            Value=GetAtt(self.api, "RootResourceId"),
        )
        self.template.add_resource(ssm_api_parent_resource_id)

        ssm_registration_resource_id = ssm.Parameter(
            "RegistrationResourceId",
            Name="/registration/resource/id",
            Type="String",
            Value=Ref(self.registration_api_resource),
        )
        self.template.add_resource(ssm_registration_resource_id)

    def create_template(self):
        self.create_api_gateway()
        self.store_ssm_parameters()
        return self.template
