The Foursquare Targeting key is a secret, so it goes in GCP Secret Manager in the prod project. The app reads it at runtime through its service account.
Do not create a prod CI/CD variable for it. The dev variable TF_VAR_foursquare_targeting_key is a leftover of the pilot and should be deleted once dev reads from Secret Manager.
The non-secret FOURSQUARE_IDENTITY_ENV = "prod" goes in the prod block of the Terraform per-environment map in dac-gcp-front-klv1ai.
