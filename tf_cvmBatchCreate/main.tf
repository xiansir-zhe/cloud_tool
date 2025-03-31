# variable "availability_zone" {
#   default = {
#     "cloud"="ap-hongkong-3"
#     "cdc"="ap-hongkong-2"
#   }
# }


# variable "instance_count" {
#   default = 1
# }

# variable "instance_type" {
#   default = "S8.MEDIUM2"    
# }

# variable "vpc_id" {
#   type = map
#   default = {
#    "cloud" = "vpc-7altrfw0"
#    "cdc" = "vpc-5s5arikw"
#   }
  
# }

# variable "subnet_id" {
#   type = map
#   default = {
#    "cloud" = "subnet-o65fi55v"
#    "cdc" = "subnet-fyrptihb"
#   }
# }

# # data "tencentcloud_images" "images" {
# #   image_type       = ["PUBLIC_IMAGE"]
# #   image_name_regex = "OpenCloudOS Server"
# # }

# data "tencentcloud_images" "images" {
#   image_type = ["PUBLIC_IMAGE"]
#   image_id =  "img-7rqxtnh9"
# }




# // create CVM instance
# resource "tencentcloud_instance" "example" {
#   count                = var.instance_count
#   instance_name        = "tf-example-${count.index}-test-1"
#   availability_zone    = var.availability_zone["cloud"]
#   image_id             = data.tencentcloud_images.images.image_id
#   instance_type        = var.instance_type
#   # dedicated_cluster_id = "cluster-7yq5nlow"
#   # instance_charge_type = "CDCPAID"
#   system_disk_type     = "CLOUD_SSD"
#   system_disk_size     = 20
#   # hostname             = "user"
#   project_id           = 0
#   vpc_id               = var.vpc_id["cloud"]
#   subnet_id            = var.subnet_id["cloud"]
#   # private_ip           = "10.2.20.12"
#   orderly_security_groups = ["sg-ikk5nxed"]

#   data_disks {
#     # data_disk_type = "CLOUD_SSD"
#     data_disk_type = "CLOUD_PREMIUM"
#     data_disk_size = 20
#     # data_disk_snapshot_id = "snap-jhkds8ex"
#     encrypt        = false

#   }

#   tags = {
#     tag = "test_batch_create"
#   }
# }



locals {
  instances = jsondecode(file("${path.module}/instances_copy.json"))
}

resource "tencentcloud_instance" "example" {
  for_each            = { for idx, instance in local.instances : idx => instance }
  instance_name       = each.value.name
  availability_zone   = each.value.availability_zone
  image_id            = each.value.image_id
  instance_type       = each.value.instance_type
  vpc_id              = each.value.vpc_id
  subnet_id           = each.value.subnet_id
  private_ip          = each.value.private_ip
  dedicated_cluster_id = "cluster-7yq5nlow"
  instance_charge_type = "CDCPAID"
  orderly_security_groups = ["sg-ikk5nxed"]

  system_disk_type     = each.value.system_disk.type
  system_disk_size     = each.value.system_disk.size

  dynamic "data_disks" {
    for_each = each.value.data_disks
    content {
      data_disk_type = data_disks.value.type
      data_disk_size = data_disks.value.size
      encrypt        = false
    }
  }

  tags = {
    tag = "test_batch_create"
  }
}