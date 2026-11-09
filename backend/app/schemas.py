from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: str
    full_name: str
    email: EmailStr
    role: str
    company_id: str | None = None
    model_config = ConfigDict(from_attributes=True)


class CompanyIn(BaseModel):
    identifier: str = Field(min_length=2, max_length=50)
    name: str = Field(min_length=2, max_length=160)
    industry: str = Field(min_length=2, max_length=100)
    description: str | None = None
    website: str | None = None


class CompanyOut(CompanyIn):
    id: str
    status: str
    model_config = ConfigDict(from_attributes=True)


class PeriodIn(BaseModel):
    year: int = Field(ge=2000, le=2100)
    month: int = Field(ge=1, le=12)
    template_id: str | None = None


class PeriodOut(BaseModel):
    id: str
    template_id: str
    year: int
    month: int
    start_date: date
    end_date: date
    status: str
    model_config = ConfigDict(from_attributes=True)


class ChangePasswordIn(BaseModel):
    current_password: str = Field(min_length=1, max_length=256)
    new_password: str = Field(min_length=12, max_length=256)


MetricKey = Literal[
    "revenue",
    "expenses",
    "customer_count",
    "new_customers",
    "employee_count",
    "cash_balance",
]


class TemplateMetricIn(BaseModel):
    metric_key: MetricKey
    label: str = Field(min_length=1, max_length=120)
    data_type: Literal["decimal", "integer"]
    unit: str = Field(min_length=1, max_length=40)
    is_required: bool = True
    minimum_value: Decimal | None = Field(default=Decimal("0"), ge=0)
    maximum_value: Decimal | None = Field(default=None, ge=0)
    sort_order: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def validate_type_and_bounds(self):
        expected_type = (
            "decimal"
            if self.metric_key in {"revenue", "expenses", "cash_balance"}
            else "integer"
        )
        if self.data_type != expected_type:
            raise ValueError(f"{self.metric_key} must use data_type={expected_type}")
        if (
            self.minimum_value is not None
            and self.maximum_value is not None
            and self.minimum_value > self.maximum_value
        ):
            raise ValueError("minimum_value cannot exceed maximum_value")
        return self


class ReportingTemplateIn(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    description: str | None = Field(default=None, max_length=2000)
    metrics: list[TemplateMetricIn] = Field(min_length=1, max_length=6)

    @model_validator(mode="after")
    def validate_unique_metric_keys(self):
        keys = [metric.metric_key for metric in self.metrics]
        if len(keys) != len(set(keys)):
            raise ValueError("Metric keys must be unique within a template")
        return self


class TemplateVersionIn(BaseModel):
    description: str | None = Field(default=None, max_length=2000)
    metrics: list[TemplateMetricIn] = Field(min_length=1, max_length=6)

    @model_validator(mode="after")
    def validate_unique_metric_keys(self):
        keys = [metric.metric_key for metric in self.metrics]
        if len(keys) != len(set(keys)):
            raise ValueError("Metric keys must be unique within a template")
        return self


class CompanySubmitterIn(BaseModel):
    full_name: str = Field(min_length=2, max_length=160)
    email: EmailStr
    password: str = Field(min_length=12, max_length=256)


class ReviewIn(BaseModel):
    comment: str | None = Field(default=None, max_length=2000)


class DecisionIn(BaseModel):
    decision: Literal["approved", "rejected"]
    reason: str | None = Field(default=None, max_length=2000)


class ReportingTemplateOut(BaseModel):
    id: str
    name: str
    description: str | None
    version: int
    is_active: bool
    metrics: list[TemplateMetricIn]
