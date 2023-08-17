
# Installation

```bash
cd ${HOME}/lepton
go build -o /tmp/ma ./machine
/tmp/ma -h
cp /tmp/ma ${GOPATH}/bin/ma
```

```bash
# for aws
ma aws -h
ma aws whoami

# for lambda-labs
ma lambda-labs -h
```

## AWS VPCs and Subnets

```bash
ma a w
ma a v l
```

```table
*-----------------------*----------------------------------*-----------*--------------------------*-----------------------------------------------------*------------*--------------*
|        VPC ID         |             VPC NAME             | VPC STATE |        SUBNET ID         |                     SUBNET NAME                     | SUBNET AZ  | SUBNET STATE |
*-----------------------*----------------------------------*-----------*--------------------------*-----------------------------------------------------*------------*--------------*
| vpc-0783178be6f46faee | my-dev-202308-D1eStP-vpc         | available | subnet-067141cd310d10862 | my-dev-202308-D1eStP-public-subnet-1                | us-east-1a | available    |
| vpc-0783178be6f46faee | my-dev-202308-D1eStP-vpc         | available | subnet-0f7a38d93587df2ba | my-dev-202308-D1eStP-public-subnet-2                | us-east-1b | available    |
| vpc-0783178be6f46faee | my-dev-202308-D1eStP-vpc         | available | subnet-0c252cee034d4097f | my-dev-202308-D1eStP-public-subnet-3                | us-east-1c | available    |
| vpc-0190a790b4fe98db1 | vpc-ci20230814155104             | available | subnet-0b8b6367a835d171c | vpc-ci20230814155104-private-us-east-1a             | us-east-1a | available    |
| vpc-0190a790b4fe98db1 | vpc-ci20230814155104             | available | subnet-01084f1639c4ff82c | vpc-ci20230814155104-private-us-east-1b             | us-east-1b | available    |
| vpc-0190a790b4fe98db1 | vpc-ci20230814155104             | available | subnet-0507b239f6dbde0fd | vpc-ci20230814155104-private-us-east-1c             | us-east-1c | available    |
| vpc-0190a790b4fe98db1 | vpc-ci20230814155104             | available | subnet-0af99672a5b5fd9f9 | vpc-ci20230814155104-public-us-east-1a              | us-east-1a | available    |
| vpc-0190a790b4fe98db1 | vpc-ci20230814155104             | available | subnet-037523bbc2cd1b57e | vpc-ci20230814155104-public-us-east-1b              | us-east-1b | available    |
| vpc-0190a790b4fe98db1 | vpc-ci20230814155104             | available | subnet-0fe0dd122bec5214b | vpc-ci20230814155104-public-us-east-1c              | us-east-1c | available    |
...
```

```bash
ma a v g vpc-0190a790b4fe98db1
```

```table
*-----------------------*----------------------*-----------*--------------------------*-----------------------------------------*------------*--------------*
|        VPC ID         |       VPC NAME       | VPC STATE |        SUBNET ID         |               SUBNET NAME               | SUBNET AZ  | SUBNET STATE |
*-----------------------*----------------------*-----------*--------------------------*-----------------------------------------*------------*--------------*
| vpc-0190a790b4fe98db1 | vpc-ci20230814155104 | available | subnet-0b8b6367a835d171c | vpc-ci20230814155104-private-us-east-1a | us-east-1a | available    |
| vpc-0190a790b4fe98db1 | vpc-ci20230814155104 | available | subnet-01084f1639c4ff82c | vpc-ci20230814155104-private-us-east-1b | us-east-1b | available    |
| vpc-0190a790b4fe98db1 | vpc-ci20230814155104 | available | subnet-0507b239f6dbde0fd | vpc-ci20230814155104-private-us-east-1c | us-east-1c | available    |
| vpc-0190a790b4fe98db1 | vpc-ci20230814155104 | available | subnet-0af99672a5b5fd9f9 | vpc-ci20230814155104-public-us-east-1a  | us-east-1a | available    |
| vpc-0190a790b4fe98db1 | vpc-ci20230814155104 | available | subnet-037523bbc2cd1b57e | vpc-ci20230814155104-public-us-east-1b  | us-east-1b | available    |
| vpc-0190a790b4fe98db1 | vpc-ci20230814155104 | available | subnet-0fe0dd122bec5214b | vpc-ci20230814155104-public-us-east-1c  | us-east-1c | available    |
*-----------------------*----------------------*-----------*--------------------------*-----------------------------------------*------------*--------------*

*-----------------------*----------------------*-------------------------------------------------------*---------------------------------------------------------------------*
|        VPC ID         |        SG ID         |                        SG NAME                        |                           SG DESCRIPTION                            |
*-----------------------*----------------------*-------------------------------------------------------*---------------------------------------------------------------------*
| vpc-0190a790b4fe98db1 | sg-02cc47f740928532f | ci20230814155104-alb-controller-sg-shared-backend     | [k8s] Shared Backend SecurityGroup for LoadBalancer                 |
| vpc-0190a790b4fe98db1 | sg-00d290a66c83e7210 | ci20230814155104-cluster-sg20230814155406010900000001 | Secondary EKS cluster security group to allow traffic from/to nodes |
| vpc-0190a790b4fe98db1 | sg-061cd77ceff6ed537 | default                                               | default VPC security group                                          |
| vpc-0190a790b4fe98db1 | sg-056f1b36cf2e21c12 | k8s-lbglooingressgrou-80fa8af7f0                      | [k8s] Managed SecurityGroup for LoadBalancer                        |
| vpc-0190a790b4fe98db1 | sg-00ce5a29a9d627bef | k8s-leptonwstestdnsco-b1fdfa0406                      | [k8s] Managed SecurityGroup for LoadBalancer
...
```

## AWS Network interfaces (ENIs)


```bash
ma a n l
```

```table
*-----------------------*--------------------------------------------------------------------------*------------*-------------*-----------------------------*-----------------------*--------------------------*------------*--------------------------------------------*
|        ENI ID         |                             ENI DESCRIPTION                              | ENI STATUS | PRIVATE IP  |         PRIVATE DNS         |        VPC ID         |        SUBNET ID         |     AZ     |                    SGS                     |
*-----------------------*--------------------------------------------------------------------------*------------*-------------*-----------------------------*-----------------------*--------------------------*------------*--------------------------------------------*
| eni-0b884a2b7352fda6f | ELB app/k8s-lbglooingressgrou-545862ab17/aaada90e1ad5ff14                | in-use     | 10.0.61.51  | ip-10-0-61-51.ec2.internal  | vpc-0190a790b4fe98db1 | subnet-037523bbc2cd1b57e | us-east-1b | sg-02cc47f740928532f, sg-056f1b36cf2e21c12 |
| eni-01c6fc4107753ebc7 | ELB app/k8s-leptonwstestdnsco-f15ddbf25d/82a6622a8ab62a2b                | in-use     | 10.0.61.60  | ip-10-0-61-60.ec2.internal  | vpc-0190a790b4fe98db1 | subnet-037523bbc2cd1b57e | us-east-1b | sg-02cc47f740928532f, sg-00ce5a29a9d627bef |
| eni-0b3716877f4a9b6bd | ELB app/k8s-leptonwstestws011-252f6a0195/ab3089ce4a4448b2                | in-use     | 10.0.61.110 | ip-10-0-61-110.ec2.internal | vpc-0190a790b4fe98db1 | subnet-037523bbc2cd1b57e | us-east-1b | sg-02cc47f740928532f, sg-0b0731f35b31c6742 |
| eni-085cd726899b6c410 | ELB app/k8s-leptonwstestws011-d2245599d5/3163a47c72d9c846                | in-use     | 10.0.61.69  | ip-10-0-61-69.ec2.internal  | vpc-0190a790b4fe98db1 | subnet-037523bbc2cd1b57e | us-east-1b | sg-02cc47f740928532f, sg-00a7b88565a037d02 |
...
```


```bash
ma a n g eni-085cd726899b6c410
```

```table
*-----------------------*-----------------------------------------------------------*------------*------------*----------------------------*-----------------------*--------------------------*------------*--------------------------------------------*
|        ENI ID         |                      ENI DESCRIPTION                      | ENI STATUS | PRIVATE IP |        PRIVATE DNS         |        VPC ID         |        SUBNET ID         |     AZ     |                    SGS                     |
*-----------------------*-----------------------------------------------------------*------------*------------*----------------------------*-----------------------*--------------------------*------------*--------------------------------------------*
| eni-085cd726899b6c410 | ELB app/k8s-leptonwstestws011-d2245599d5/3163a47c72d9c846 | in-use     | 10.0.61.69 | ip-10-0-61-69.ec2.internal | vpc-0190a790b4fe98db1 | subnet-037523bbc2cd1b57e | us-east-1b | sg-02cc47f740928532f, sg-00a7b88565a037d02 |
*-----------------------*-----------------------------------------------------------*------------*------------*----------------------------*-----------------------*--------------------------*------------*--------------------------------------------*
```

```bash
# to pick subnet ID + security group IDs
ma a v l
ma a v g vpc-02f3af6ef3ce509e7

# to create an ENI
ma a n c \
--subnet-id subnet-0a4b3ec9cca34bc10 \
--sg-ids sg-0d3bdbd671a4e34c8 \
--name test \
--description test

# to list ENIs
ma a n l
ma a n g eni-0d858b07277d087c9

# to delete an ENI
ma a n d eni-0d858b07277d087c9
```
