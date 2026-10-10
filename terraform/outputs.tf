output "pg_host" {
  description = "Host do Postgre"
  value       = aiven_pg.tse.service_host
}

output "pg_port" {
  description = "Porta do Postgre"
  value       = aiven_pg.tse.service_port
}

output "pg_database" {
  description = "Nome do banco"
  value       = aiven_pg_database.tse_db.database_name
}

output "pg_service_uri" {
  description = "URI completa de conexão"
  value       = aiven_pg.tse.service_uri
  sensitive   = true
}
