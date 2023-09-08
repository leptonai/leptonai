# LEP-2345: Rate Control

## Motivation

In business-to-business-to-consumer (B2B2C) scenarios, service providers need to apply rate control on the API calls from their business partners. 

For example, a service provider may want to limit the number of API calls from a business partner to 1000 per hour. The rate control feature is to help service providers to achieve this goal.

## Functional Requirements

The functional requirement is available at [2345-Rate-Control](https://www.notion.so/leptonai/2345-Rate-Control-adceeffea43944b9b5111099597b53ad?pvs=4)

## Design

TBD, need to be discussed.

## Timeline and Release Criteria

### Alpha 

For each deployment, the rate control feature is disabled by default. The ML service provider can enable the feature by setting the `rateControlPolicy` field during the deployment creation.  


