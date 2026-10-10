terraform {
  required_version = ">= 1.5"
  required_providers {
    aiven = {
      source  = "aiven/aiven"
      version = ">= 4.0.0, < 5.0.0"
    }
  }
}

provider "aiven" {
  api_token = var.aiven_api_token
}

resource "aiven_pg" "tse" {
  project      = var.aiven_project
  service_name = "pg-tse-2022"
  cloud_name   = "do-nyc"
  plan         = "free-1-1gb"

  termination_protection = false
}

resource "aiven_pg_database" "tse_db" {
  project       = var.aiven_project
  service_name  = aiven_pg.tse.service_name
  database_name = "tse_dados"
}
