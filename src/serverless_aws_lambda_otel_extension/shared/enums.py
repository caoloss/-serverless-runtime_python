from enum import Enum


class AwsLambdaRuntimeAPIExtensionEventEnum(Enum):
    INVOKE = "INVOKE"
    SHUTDOWN = "SHUTDOWN"


class AwsLambdaRuntimeAPIExtensionResponseEventEnum(Enum):
    EventInvoke = "EventInvoke"
    EventShutdown = "EventShutdown"
