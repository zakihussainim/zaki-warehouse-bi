variable "project_prefix" {
  description = "Prefix used for naming all resources in this module"
  type        = string
}

variable "database_name" {
  description = "Name of the database created inside the Redshift Serverless namespace"
  type        = string
  default     = "salesdw"
}