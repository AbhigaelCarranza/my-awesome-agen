terraform {
  backend "gcs" {
    bucket = "rag-adk-461121-terraform-state"
    prefix = "my-awesome-agen/prod"
  }
}
