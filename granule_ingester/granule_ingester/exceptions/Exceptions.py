class PipelineBuildingError(Exception):
    pass


class PipelineRunningError(Exception):
    pass


class TileProcessingError(Exception):
    pass


class ConnectionErrorRabbitMQ(Exception):
    pass
