variable "aiven_api_token" {
  description = "Token de API da Aiven"
  type        = string
  sensitive   = true
}

variable "aiven_project" {
  description = "Nome do projeto na Aiven"
  type        = string
}
