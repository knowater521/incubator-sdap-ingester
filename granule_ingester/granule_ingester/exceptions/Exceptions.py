class PipelineBuildingError(Exception):
    pass


class PipelineRunningError(Exception):
    pass


class TileProcessingError(Exception):
    pass


class LostConnectionError(Exception):
    pass


class RabbitMQLostConnectionError(LostConnectionError):
    pass


class CassandraLostConnectionError(LostConnectionError):
    pass


class FailedHealthCheckError(Exception):
    pass


class CassandraFailedHealthCheckError(FailedHealthCheckError):
    pass


class SolrFailedHealthCheckError(FailedHealthCheckError):
    pass


class RabbitMQFailedHealthCheckError(FailedHealthCheckError):
    pass
