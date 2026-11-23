
from typing import List, Literal
from pydantic import BaseModel, Field


class EvidenceSource(BaseModel):
    url: str
    title: str = ""
    source_type: Literal[
        "Official",
        "Third-party",
        "Unverified"
    ]
    supports: str
    research_method: Literal[
        "Search",
        "Crawl",
        "Manual verification"
    ]
    excerpt: str = ""


class AppResearch(BaseModel):
    app_id: int
    app_name: str
    category: str
    description: str

    auth_methods: List[str] = Field(default_factory=list)

    credential_access: Literal[
    "Self-serve free",
    "Self-serve paid",
    "Admin approval",
    "Partnership/contact sales",
    "Controlled / plan-dependent",
    "Unknown"
]

    api_type: List[str] = Field(default_factory=list)
    api_breadth: str

    mcp_available: Literal[
        "Yes",
        "No",
        "Unknown"
    ]

    mcp_evidence: str = "Not verified"

    buildability: Literal[
        "Easy",
        "Medium",
        "Difficult",
        "Not Buildable",
        "Unknown"
    ]

    blocker: str

    evidence: List[EvidenceSource] = Field(
        default_factory=list
    )

    confidence: Literal[
        "High",
        "Medium",
        "Low"
    ]

    research_notes: str = ""
