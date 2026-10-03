from sqlalchemy import Column, String, Numeric, Integer, Boolean, ForeignKey
from backend.app.models.base import Base, TimestampMixin, generate_uuid

class MuleGraphNode(Base, TimestampMixin):
    __tablename__ = "mule_graph_nodes"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    account_number = Column(String(20), unique=True, nullable=False, index=True)
    cluster_id = Column(String(64), nullable=True, index=True)
    node_type = Column(String(30), default="SUSPECT_MULE", nullable=False)  # VICTIM, SUSPECT_MULE, CASH_OUT_AGENT
    risk_score = Column(Numeric(4, 3), default=0.50, nullable=False)
    in_degree = Column(Integer, default=0, nullable=False)
    out_degree = Column(Integer, default=0, nullable=False)
    is_frozen = Column(Boolean, default=False, nullable=False)

    def __repr__(self):
        return f"<MuleGraphNode acc={self.account_number} cluster={self.cluster_id} type={self.node_type}>"

class MuleGraphEdge(Base, TimestampMixin):
    __tablename__ = "mule_graph_edges"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    source_account = Column(String(20), nullable=False, index=True)
    target_account = Column(String(20), nullable=False, index=True)
    cluster_id = Column(String(64), nullable=True, index=True)
    total_amount = Column(Numeric(14, 2), default=0.00, nullable=False)
    transaction_count = Column(Integer, default=1, nullable=False)
    is_fan_out = Column(Boolean, default=False, nullable=False)

    def __repr__(self):
        return f"<MuleGraphEdge {self.source_account} -> {self.target_account} amount={self.total_amount}>"
