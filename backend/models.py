from sqlalchemy import Column, Integer, String, Float, JSON, DateTime
from sqlalchemy.sql import func
from database import Base


class ScenarioRecord(Base):
    """Persisted scenario definition."""
    __tablename__ = "scenarios"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    description = Column(String, default="")
    request_data = Column(JSON, nullable=False)
    tool_overrides = Column(JSON, default={})
    pre_inject = Column(JSON, nullable=True)
    expected_violations = Column(JSON, default=[])
    expected_outcome = Column(String, default="")
    created_at = Column(DateTime, server_default=func.now())


class RunRecord(Base):
    """Persisted result of running a scenario through the pipeline."""
    __tablename__ = "runs"

    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(String, unique=True, index=True, nullable=False)
    scenario_name = Column(String, index=True, nullable=False)
    status = Column(String, default="pending")

    # Serialized trace, violations, attack paths, defenses
    trace_json = Column(JSON, default=[])
    violations_json = Column(JSON, default=[])
    attack_paths_json = Column(JSON, default=[])
    defenses_json = Column(JSON, default=[])

    # Metrics
    latency_ms = Column(Integer, default=0)
    error = Column(String, default="")

    started_at = Column(String, default="")
    finished_at = Column(String, default="")
    created_at = Column(DateTime, server_default=func.now())
