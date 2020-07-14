class PipelineBuildingError(Exception):
    pass


class PipelineRunningError(Exception):
    pass


class TileProcessingError(Exception):
    pass


class RabbitMQConnectionError(Exception):
    pass


class CassandraConnectionError(Exception):
    pass


class FailedHealthCheckError(Exception):
    pass


class CassandraFailedHealthCheckError(FailedHealthCheckError):
    pass


class SolrFailedHealthCheckError(FailedHealthCheckError):
    pass


class RabbitMQFailedHealthCheckError(FailedHealthCheckError):
    pass


