import { request } from './http';
import type { AcceptTermsPayload, AcceptTermsResponse, TermsStatus } from '@/types/terms';

export function getTermsStatus(): Promise<TermsStatus> {
    return request<TermsStatus>('/me/terms-status');
}

export function acceptTerms(payload: AcceptTermsPayload): Promise<AcceptTermsResponse> {
    return request<AcceptTermsResponse>('/me/accept-terms', {
        method: 'POST',
        json: payload
    });
}
