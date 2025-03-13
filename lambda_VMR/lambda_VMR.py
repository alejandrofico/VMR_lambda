import json
import os
import requests 
import logging

#Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

#Load API key details
API_KEY_NAME = os.getenv("API_KEY", "x-api-key")
API_KEY_VALUE = os.getenv("API_KEY_VALUE")

if not API_KEY_VALUE:
    logger.error("API_KEY_VALUE environment variable is missing. Lambda will fail.")

#Flows API endpoints, region-based
FLOWS_API_ENDPOINTS = {
    "US" : "https://api-us1cqa.ficoflows-cqa.net/solutions/483-test/cases",
    "CA" : "https://api-",
    "EMEA" : "https://api-"
}

def identify_region(aws_region):
    """ Maps AWS region to Flows API region"""
    region_mapping = {
        "us-east-1" : "US",
        "us-west-2" : "US",
        "ca-central-1" : "CA",
        "eu-west-1" : "EMEA",
        "eu-central-1" : "EMEA"
    }
    return region_mapping.get(aws_region, "US")

def send_to_flows(region, payload):
    """ Sends the full payload to the correct flows API"""
    api_url = FLOWS_API_ENDPOINTS.get(region)
    
    if not api_url:
        logger.error(f"No API endpoint found for region: {region}")
        return False
    
    headers = {
        "Content-Type" : "application/json", 
        API_KEY_NAME : API_KEY_VALUE
        }

    try:
        response = requests.post(api_url, json=payload, headers=headers, timeout=5)
        response.raise_for_status()
        logger.info(f"Successfully sent payload to {region} Flows API: {api_url}")
        return True
    
    except requests.exceptions.RequestException as e:
        logger.error(f"Error sending payload to Flows API: {e}")
        return False

def lambda_handler(event, context):
    """AWS Lambda entry point."""
    try:
        for record in event.get("Records", []):
            try:
                # Get full payload from SNS message
                sns_message = json.loads(record["Sns"]["Message"])

                #Extract Alert Info and Records
                full_payload = {
                    "Alert_Info" : sns_message.get("Alert_Info", {}),
                    "Records" : event.get("Records", [])
                }

                # Identify the correct Flows API region
                aws_region = full_payload["Alert_Info"].get("awsRegion", "us-east-1")
                flows_region = identify_region(aws_region)

                # Send full payload to Flows API
                success = send_to_flows(flows_region, full_payload)

                if not success:
                    logger.warning("Failed to send alert to Flows API. Keeping SNS message for ticketing.")
            except Exception as inner_e:
                logger.error(f"Error processing SNS record: {inner_e}")    

        return {"status" : "Processing complete"}

    
    except Exception as e:
        logger.error(f"Error in lambda function: {e}")
        return {"status" : "Error", "message" :str(e)}
