# Meta Developer App Setup Checklist — Sprint 6A

Meta Ads API is not active.

Sprint 6A prepares setup, security, OAuth, token storage, and QA design only. No live OAuth, no token storage, no live API calls, and no production sync were implemented.

Before implementing live OAuth, verify current Meta requirements against official Meta for Developers documentation, because permissions, app review requirements, and access levels may change.

## Product-owner checklist

- [ ] Meta Developer account required.
- [ ] Meta Developer App required.
- [ ] App type/use case decision documented before implementation.
- [ ] Business Manager / Business Portfolio requirement checked for the chosen Marketing API path.
- [ ] Test user / test business setup prepared for staging-only validation.
- [ ] Redirect URI setup prepared for staging and production domains, but no live redirect is implemented in Sprint 6A.
- [ ] App domain setup prepared for the approved Sellora domains.
- [ ] Privacy Policy URL requirement prepared and owned by the product owner.
- [ ] Terms of Service URL requirement prepared and owned by the product owner.
- [ ] Data deletion instructions URL requirement prepared and owned by the product owner.
- [ ] App Review preparation plan created before requesting production permissions.
- [ ] Permission request plan follows least privilege and starts with read-only advertising insights.
- [ ] Screencast/demo preparation planned with a synthetic workspace and synthetic advertising data.
- [ ] Least-privilege permission principle approved by engineering and product.
- [ ] No customer data sent to Meta during read-only sync.

## Implementation gate for future sprints

Sprint 6B or later may start implementation only after this checklist is re-verified against official Meta documentation, staging domains are known, legal URLs are available, and a safe non-production workspace is prepared.

No real Meta app credentials, client secrets, app secrets, ad account IDs, business IDs, or access tokens should be committed to code, docs, tests, screenshots, or PR text.

## Official references to re-check

- Meta permissions reference: https://developers.facebook.com/docs/permissions/
- Meta App Review tutorial: https://developers.facebook.com/documentation/resp-plat-initiatives/appreview/tutorial
- Meta Login manual flow guide: https://developers.facebook.com/documentation/facebook-login/guides/advanced/manual-flow
- Meta Login security guide: https://developers.facebook.com/documentation/facebook-login/security
