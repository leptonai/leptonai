# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel
from loguru import logger

from .common import Metadata


class ReservationStatusEnum(str, Enum):
    """Phase of a node reservation, mirroring the console's ReservationStatusEnum."""

    PendingApproval = "PendingApproval"
    Rejected = "Rejected"
    WaitingEffective = "WaitingEffective"
    Reserving = "Reserving"
    Reserved = "Reserved"
    Expired = "Expired"
    Unknown = "UNK"

    @classmethod
    def _missing_(cls, value):
        logger.trace(f"Unknown value: {value} for ReservationStatusEnum")
        return cls.Unknown


class NodeReservationTimeRule(BaseModel):
    # Unix timestamps in SECONDS, per the api-server
    # NodeReservationRequestSpecTimeRule (these are serialized with time.Unix()).
    start_timestamp: Optional[int] = None
    end_timestamp: Optional[int] = None


class NodeReservationSpec(BaseModel):
    users: Optional[List[str]] = None
    desired_nodes: Optional[int] = None
    approved_nodes: Optional[int] = None
    time_rule: Optional[NodeReservationTimeRule] = None
    created_by: Optional[str] = None
    # The console type carries display_name in spec, but the api-server actually
    # serializes the display name into metadata.name. Keep it optional so we can
    # fall back to it when present.
    display_name: Optional[str] = None


class NodeReservationStatus(BaseModel):
    phase: Optional[ReservationStatusEnum] = None
    # reserved_count is omitempty on the wire, so 0 may be absent.
    reserved_count: int = 0
    reserved_nodes: Optional[List[str]] = None


class NodeReservation(BaseModel):
    # metadata.created_at is in MILLISECONDS (api-server uses CreationTimestamp
    # .UnixMilli()), unlike spec.time_rule timestamps which are in seconds.
    metadata: Metadata
    spec: NodeReservationSpec
    status: Optional[NodeReservationStatus] = None
