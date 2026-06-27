export interface TermsStatus {
    accepted: boolean;
    current_version: string;
    accepted_version: string | null;
    accepted_at: string | null;
}

export interface AcceptTermsPayload {
    terms_version: string;
}

export interface AcceptTermsResponse {
    accepted: boolean;
    terms_version: string;
    accepted_at: string;
}
