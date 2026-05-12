/*
S3 モジュールで使用する入力変数を定義する。

- bucket_name: S3 バケット名
- tags: S3 バケットに適用するタグ
*/
# バケット名を受け取る。
variable "bucket_name" {
  description = "Name of the S3 bucket."
  type        = string
}

# 共通タグを受け取る。
variable "tags" {
  description = "Tags to apply to the S3 bucket."
  type        = map(string)
}
