from app.domain.candidates import CandidateStatus, SourceCandidate


class DedupeService:
    """Check candidates against existing records to prevent duplicates.

    Dedupe priority:
    1. prospect_email
    2. prospect_linkedin_url
    3. company_domain + prospect_name
    4. company_domain + prospect_title
    """

    def __init__(self, existing_candidates: list[SourceCandidate] | None = None) -> None:
        existing = existing_candidates or []
        self._email_index = {
            c.prospect_email: c for c in existing if c.prospect_email
        }
        self._linkedin_index = {
            c.prospect_linkedin_url: c for c in existing if c.prospect_linkedin_url
        }
        self._domain_name_index = {
            (c.company_domain, c.prospect_name): c
            for c in existing
            if c.company_domain and c.prospect_name
        }
        self._domain_title_index = {
            (c.company_domain, c.prospect_title): c
            for c in existing
            if c.company_domain and c.prospect_title
        }

    def find_duplicate(self, candidate: SourceCandidate) -> SourceCandidate | None:
        if candidate.prospect_email and candidate.prospect_email in self._email_index:
            return self._email_index[candidate.prospect_email]
        if (
            candidate.prospect_linkedin_url
            and candidate.prospect_linkedin_url in self._linkedin_index
        ):
            return self._linkedin_index[candidate.prospect_linkedin_url]
        if candidate.company_domain and candidate.prospect_name:
            key = (candidate.company_domain, candidate.prospect_name)
            if key in self._domain_name_index:
                return self._domain_name_index[key]
        if candidate.company_domain and candidate.prospect_title:
            key = (candidate.company_domain, candidate.prospect_title)
            if key in self._domain_title_index:
                return self._domain_title_index[key]
        return None

    def generate_dedupe_key(self, candidate: SourceCandidate) -> str:
        if candidate.prospect_email:
            return f"email:{candidate.prospect_email}"
        if candidate.prospect_linkedin_url:
            return f"linkedin:{candidate.prospect_linkedin_url}"
        if candidate.company_domain and candidate.prospect_name:
            return f"domain_name:{candidate.company_domain}:{candidate.prospect_name}"
        if candidate.company_domain and candidate.prospect_title:
            return f"domain_title:{candidate.company_domain}:{candidate.prospect_title}"
        return f"unknown:{candidate.candidate_id}"

    def mark_duplicate(self, candidate: SourceCandidate, duplicate_of: SourceCandidate) -> None:
        candidate.candidate_status = CandidateStatus.DUPLICATE
        candidate.duplicate_of = duplicate_of.candidate_id
        candidate.dedupe_key = self.generate_dedupe_key(candidate)
