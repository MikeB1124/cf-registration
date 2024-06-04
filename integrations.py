from stacker.blueprints.base import Blueprint
from troposphere import (
    Ref,
    apigateway,
)


class Registration(Blueprint):
    VARIABLES = {"env-dict": {"type": dict}}

    def create_template(self):
        registration_api_deoployment = self.template.add_resource(
            apigateway.Deployment(
                "RegistrationApiDeployment",
                RestApiId="{{resolve:ssm:/registration/api/id}}",
            )
        )

        registration_api_stage = self.template.add_resource(
            apigateway.Stage(
                "RegistrationApiStage",
                DeploymentId=Ref(registration_api_deoployment),
                RestApiId="{{resolve:ssm:/registration/api/id}}",
                StageName="api",
            )
        )

        registration_usage_plan = self.template.add_resource(
            apigateway.UsagePlan(
                "RegistrationUsagePlan",
                DependsOn=registration_api_stage,
                UsagePlanName=self.get_variables()["env-dict"]["ApiUsagePlanName"],
                ApiStages=[
                    apigateway.ApiStage(
                        ApiId="{{resolve:ssm:/registration/api/id}}",
                        Stage="api",
                    )
                ],
                Description="Registration Usage Plan",
                Quota=apigateway.QuotaSettings(
                    Limit=100000,
                    Period="MONTH",
                ),
                Throttle=apigateway.ThrottleSettings(
                    BurstLimit=100,
                    RateLimit=50,
                ),
            )
        )

        registration_api_key = self.template.add_resource(
            apigateway.ApiKey(
                "RegistrationApiKey",
                Name=self.get_variables()["env-dict"]["ApiKeyName"],
                Enabled=True,
            )
        )

        self.template.add_resource(
            apigateway.UsagePlanKey(
                "RegistrationUsagePlanKey",
                DependsOn=registration_usage_plan,
                KeyId=Ref(registration_api_key),
                KeyType="API_KEY",
                UsagePlanId=Ref(registration_usage_plan),
            )
        )
