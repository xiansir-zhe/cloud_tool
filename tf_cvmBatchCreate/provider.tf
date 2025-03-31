terraform {
  required_providers {
    tencentcloud = {
      source = "tencentcloudstack/tencentcloud"
      # 通过version指定版本；若不指定，默认为最新版本
      #   version = ">=1.81.60"
    }
  }
}



#Account: 100037194712
provider "tencentcloud" {
  secret_id = "XXX"
  secret_key = "XXX"
  region = "ap-hongkong"
#   alias = hongkong
} 