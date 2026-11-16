# The providers the Terraform course uses. The Dockerfile mirrors them into the image (tofu providers mirror),
# checked against .terraform.lock.hcl, so `tofu init` in a workspace needs no network. To update: change a version,
# then run  tofu providers lock -platform=linux_amd64 -platform=linux_arm64  here and commit the lock file.
terraform {
  required_providers {
    local  = { source = "hashicorp/local", version = "2.9.1" }
    random = { source = "hashicorp/random", version = "3.9.1" }
  }
}
