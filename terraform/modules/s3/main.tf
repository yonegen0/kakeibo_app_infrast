/*
S3 モジュールです。
S3 バケットを作成し、パブリックアクセスを禁止します。

- aws_s3_bucket: S3 バケットを作成する。
- aws_s3_bucket_public_access_block: パブリックアクセスをブロックする。
*/

# S3バケット本体を作成する。
resource "aws_s3_bucket" "this" {
  bucket = var.bucket_name
  tags   = var.tags
}

# パブリックアクセスを全面的に禁止する設定を適用する。
resource "aws_s3_bucket_public_access_block" "this" {
  bucket = aws_s3_bucket.this.id

  block_public_acls       = true
  ignore_public_acls      = true
  block_public_policy     = true
  restrict_public_buckets = true
}
