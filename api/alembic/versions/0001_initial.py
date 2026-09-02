"""initial schema: material, item, image, detection, reuse_suggestion, rag_chunk"""
import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision, down_revision = "0001", None

def upgrade():
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.create_table("material",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(64), unique=True, nullable=False),
        sa.Column("category", sa.String(32), nullable=False),          # metal|plastic|wood|composite|other
        sa.Column("recyclable", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("disposal_de", sa.String(128)),                        # e.g. "Wertstofftonne", "Schadstoffmobil"
    )
    op.create_table("image",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("path", sa.String(256), nullable=False),
        sa.Column("width", sa.Integer), sa.Column("height", sa.Integer),
        sa.Column("captured_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("device", sa.String(96)),
    )
    op.create_table("item",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("label", sa.String(64), nullable=False, index=True),
        sa.Column("material_id", sa.Integer, sa.ForeignKey("material.id", ondelete="SET NULL")),
        sa.Column("condition", sa.String(32)),
        sa.Column("quantity", sa.Integer, nullable=False, server_default="1"),
        sa.Column("location", sa.String(64)),
        sa.Column("status", sa.String(16), nullable=False, server_default="available"),  # available|reserved|reused|disposed
        sa.Column("first_image_id", sa.Integer, sa.ForeignKey("image.id", ondelete="SET NULL")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_table("detection",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column("image_id", sa.Integer, sa.ForeignKey("image.id", ondelete="CASCADE"), nullable=False),
        sa.Column("item_id", sa.Integer, sa.ForeignKey("item.id", ondelete="SET NULL"), index=True),
        sa.Column("cls", sa.String(64), nullable=False),
        sa.Column("conf", sa.Float, nullable=False),
        sa.Column("x1", sa.Float), sa.Column("y1", sa.Float), sa.Column("x2", sa.Float), sa.Column("y2", sa.Float),
        sa.Column("material_pred", sa.String(64)), sa.Column("material_conf", sa.Float),
        sa.Column("condition_pred", sa.String(32)), sa.Column("vlm_backend", sa.String(32)),
        sa.Column("infer_ms", sa.Float), sa.Column("fps", sa.Float), sa.Column("device", sa.String(96)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), index=True),
    )
    op.create_table("reuse_suggestion",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("item_id", sa.Integer, sa.ForeignKey("item.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("text", sa.Text, nullable=False),
        sa.Column("sources", sa.JSON),
        sa.Column("model", sa.String(64)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table("rag_chunk",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("doc", sa.String(128), nullable=False, index=True),
        sa.Column("section", sa.String(256)),
        sa.Column("lang", sa.String(2)),
        sa.Column("text", sa.Text, nullable=False),
        sa.Column("embedding", Vector(768)),
    )
    op.execute("CREATE INDEX rag_chunk_emb_idx ON rag_chunk USING hnsw (embedding vector_cosine_ops)")

def downgrade():
    for t in ["rag_chunk", "reuse_suggestion", "detection", "item", "image", "material"]:
        op.drop_table(t)
