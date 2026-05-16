from pydantic import BaseModel, ConfigDict, Field, field_validator


class CompanyProfile(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str
    description: str
    website: str | None = None


class ICP(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    company_size: str
    regions: list[str] = Field(default_factory=list)
    industries: list[str] = Field(default_factory=list)
    exclusions: list[str] = Field(default_factory=list)


class BuyerPersona(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    title_patterns: list[str]
    priorities: list[str] = Field(default_factory=list)
    tone: str


class ValueProp(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    id: str
    pain: str
    outcome: str
    proof: str | None = None


class CaseStudy(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    id: str
    title: str
    summary: str
    result: str | None = None
    use_when: list[str] = Field(default_factory=list)


class Objection(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    objection: str
    response: str


class MessageRules(BaseModel):
    max_words_email: int = Field(default=120, ge=40, le=250)
    max_words_linkedin: int = Field(default=80, ge=20, le=150)
    avoid_phrases: list[str] = Field(default_factory=list)
    required_traits: list[str] = Field(default_factory=list)
    call_to_action_examples: list[str] = Field(default_factory=list)


class SalesPlaybook(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    company: CompanyProfile
    icp: ICP
    buyer_personas: list[BuyerPersona]
    value_props: list[ValueProp]
    case_studies: list[CaseStudy] = Field(default_factory=list)
    objections: list[Objection] = Field(default_factory=list)
    message_rules: MessageRules = Field(default_factory=MessageRules)

    @field_validator("buyer_personas", "value_props")
    @classmethod
    def list_must_not_be_empty(cls, value: list[object]) -> list[object]:
        if not value:
            raise ValueError("list must contain at least one item")
        return value
