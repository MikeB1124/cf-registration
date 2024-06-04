from stacker.blueprints.base import Blueprint
from troposphere import (
    Ref,
    GetAtt,
    iam,
    awslambda,
    Parameter,
    Sub,
    apigateway,
)


class Registration(Blueprint):
    VARIABLES = {"env-dict": {"type": dict}}

    def get_existing_registration_bucket(self):
        self.existing_registration_bucket = self.template.add_parameter(
            Parameter(
                "RegistrationS3Bucket",
                Type="String",
                Default=self.get_variables()["env-dict"]["BucketName"],
            )
        )

    def create_registration_lambda(self):
        lambda_role = self.template.add_resource(
            iam.Role(
                "RegistrationLambdaExecutionRole",
                AssumeRolePolicyDocument={
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Effect": "Allow",
                            "Principal": {
                                "Service": [
                                    "lambda.amazonaws.com",
                                    "apigateway.amazonaws.com",
                                ]
                            },
                            "Action": ["sts:AssumeRole"],
                        }
                    ],
                },
                Policies=[
                    iam.Policy(
                        PolicyName="RegistrationLambdaS3Policy",
                        PolicyDocument={
                            "Version": "2012-10-17",
                            "Statement": [
                                {
                                    "Effect": "Allow",
                                    "Action": ["s3:GetObject"],
                                    "Resource": [
                                        Sub(
                                            "arn:aws:s3:::${BucketName}/*",
                                            BucketName=self.get_variables()["env-dict"][
                                                "BucketName"
                                            ],
                                        )
                                    ],
                                }
                            ],
                        },
                    ),
                    iam.Policy(
                        PolicyName="RegistrationLambdaLogPolicy",
                        PolicyDocument={
                            "Version": "2012-10-17",
                            "Statement": [
                                {
                                    "Effect": "Allow",
                                    "Action": "logs:CreateLogGroup",
                                    "Resource": Sub(
                                        "arn:aws:logs:${AWS::Region}:${AWS::AccountId}:*"
                                    ),
                                },
                                {
                                    "Effect": "Allow",
                                    "Action": [
                                        "logs:CreateLogStream",
                                        "logs:PutLogEvents",
                                    ],
                                    "Resource": [
                                        Sub(
                                            "arn:aws:logs:${AWS::Region}:${AWS::AccountId}:log-group:/aws/lambda/${LambdaName}:*",
                                            LambdaName=self.get_variables()["env-dict"][
                                                "RegistrationLambdaName"
                                            ],
                                        )
                                    ],
                                },
                            ],
                        },
                    ),
                    iam.Policy(
                        PolicyName="RegistrationLambdaSecretsManagerPolicy",
                        PolicyDocument={
                            "Version": "2012-10-17",
                            "Statement": [
                                {
                                    "Effect": "Allow",
                                    "Action": ["secretsmanager:GetSecretValue"],
                                    "Resource": [
                                        Sub(
                                            "arn:aws:secretsmanager:${AWS::Region}:${AWS::AccountId}:secret:${SecretId}-yuRaM1",
                                            SecretId=self.get_variables()["env-dict"][
                                                "SharedSecretsId"
                                            ],
                                        )
                                    ],
                                }
                            ],
                        },
                    ),
                ],
            )
        )

        registration_lambda_function = awslambda.Function(
            "RegistrationLambdaFunction",
            FunctionName=self.get_variables()["env-dict"]["RegistrationLambdaName"],
            Code=awslambda.Code(
                S3Bucket=Ref(self.existing_registration_bucket),
                S3Key=Sub(
                    "lambdas/${LambdaName}.zip",
                    LambdaName=self.get_variables()["env-dict"][
                        "RegistrationLambdaName"
                    ],
                ),
            ),
            Environment=awslambda.Environment(
                Variables={
                    "SHARED_SECRETS": self.get_variables()["env-dict"][
                        "SharedSecretsId"
                    ]
                }
            ),
            Handler="handler",
            Runtime="provided.al2023",
            Role=GetAtt(lambda_role, "Arn"),
        )
        self.template.add_resource(registration_lambda_function)

        signup_api_method = apigateway.Method(
            "SignupMethod",
            DependsOn=registration_lambda_function,
            AuthorizationType="NONE",
            ApiKeyRequired=True,
            HttpMethod="POST",
            RestApiId="{{resolve:ssm:/registration/api/id}}",
            ResourceId="{{resolve:ssm:/signup/resource/id}}",
            Integration=apigateway.Integration(
                IntegrationHttpMethod="POST",
                Type="AWS_PROXY",
                Uri=Sub(
                    "arn:aws:apigateway:${AWS::Region}:lambda:path/2015-03-31/functions/${LambdaArn}/invocations",
                    LambdaArn=GetAtt(registration_lambda_function, "Arn"),
                ),
            ),
        )
        self.template.add_resource(signup_api_method)

        login_api_method = apigateway.Method(
            "LoginMethod",
            DependsOn=registration_lambda_function,
            AuthorizationType="NONE",
            ApiKeyRequired=True,
            HttpMethod="POST",
            RestApiId="{{resolve:ssm:/registration/api/id}}",
            ResourceId="{{resolve:ssm:/login/resource/id}}",
            Integration=apigateway.Integration(
                IntegrationHttpMethod="POST",
                Type="AWS_PROXY",
                Uri=Sub(
                    "arn:aws:apigateway:${AWS::Region}:lambda:path/2015-03-31/functions/${LambdaArn}/invocations",
                    LambdaArn=GetAtt(registration_lambda_function, "Arn"),
                ),
            ),
        )
        self.template.add_resource(login_api_method)



        self.template.add_resource(
            awslambda.Permission(
                "SignupInvokePermission",
                DependsOn=registration_lambda_function,
                Action="lambda:InvokeFunction",
                FunctionName=self.get_variables()["env-dict"][
                    "RegistrationLambdaName"
                ],
                Principal="apigateway.amazonaws.com",
                SourceArn=Sub(
                    "arn:aws:execute-api:${AWS::Region}:${AWS::AccountId}:${ApiId}/*/POST/signup",
                    ApiId="{{resolve:ssm:/registration/api/id}}",
                ),
            )
        )

        self.template.add_resource(
            awslambda.Permission(
                "LoginInvokePermission",
                DependsOn=registration_lambda_function,
                Action="lambda:InvokeFunction",
                FunctionName=self.get_variables()["env-dict"][
                    "RegistrationLambdaName"
                ],
                Principal="apigateway.amazonaws.com",
                SourceArn=Sub(
                    "arn:aws:execute-api:${AWS::Region}:${AWS::AccountId}:${ApiId}/*/POST/login",
                    ApiId="{{resolve:ssm:/registration/api/id}}",
                ),
            )
        )

    def create_template(self):
        self.get_existing_registration_bucket()
        self.create_registration_lambda()
        return self.template
