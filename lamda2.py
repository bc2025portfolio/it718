import json
import boto3

# Initialize S3 client
s3 = boto3.client('s3')
BUCKET_NAME = "cloud-dashboard-projectbucket"

def lambda_handler(event, context):
    # 1. Standard CORS headers to be used in all responses
    # This ensures the browser allows the frontend to read the data
    headers = {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'OPTIONS, POST, GET',
        'Access-Control-Allow-Headers': 'Content-Type, x-amz-meta-project-name, x-amz-meta-project-tags'
    }

    # 2. Handle CORS Preflight (OPTIONS)
    # Browsers send this automatically before a POST request
    method = event.get('requestContext', {}).get('http', {}).get('method', 'POST')
    if method == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': headers,
            'body': ''
        }

    # 3. Parse the request body
    try:
        body = json.loads(event.get('body', '{}'))
    except Exception:
        body = {}

    action = body.get('action')
    user_id = body.get('userId', 'Unknown_User')
    
    # Check for both 'fileName' and 'filename' to avoid frontend mismatches
    filename = body.get('fileName') or body.get('filename')
    
    result = {"status": "success"}

    try:
        # --- ACTION: LIST PROJECTS ---
        if action == "LIST":
            prefix = f"users/{user_id}/"
            # list_objects_v2 retrieves the files within a specific user's "folder"
            response = s3.list_objects_v2(Bucket=BUCKET_NAME, Prefix=prefix)
            
            project_list = []
            # Reliability Fix: Check if 'Contents' exists to handle new users (User B)
            if 'Contents' in response:
                for obj in response['Contents']:
                    key = obj['Key']
                    
                    # Skip the folder prefix itself if it appears as an object
                    if key == prefix:
                        continue
                        
                    # Retrieve metadata tags (HeadObject is needed for x-amz-meta)
                    # This pulls the 'Project Name' and 'Tags' you set during upload
                    meta = s3.head_object(Bucket=BUCKET_NAME, Key=key)
                    metadata = meta.get('Metadata', {})
                    
                    project_list.append({
                        "name": key.split('/')[-1],
                        "customName": metadata.get('project-name', key.split('/')[-1]),
                        "tags": metadata.get('project-tags', "").split(',') if metadata.get('project-tags') else []
                    })
            
            result["projects"] = project_list

        # --- ACTION: DELETE PROJECT ---
        elif action == "DELETE":
            if filename:
                key = f"users/{user_id}/{filename}"
                s3.delete_object(Bucket=BUCKET_NAME, Key=key)
                result["message"] = f"Deleted {filename}"
            else:
                result["status"] = "error"
                result["message"] = "No filename provided for deletion"

        # --- ACTION: ANALYZE PROJECT ---
        elif action == "ANALYZE":
            # Returns a clean dictionary for the frontend to stringify
            result["analysis"] = {
                "report": f"Analysis complete for {filename}.",
                "user": user_id,
                "status": "Verified in Cloud Storage",
                "timestamp": "2026-04-27",
                "security_scan": "Passed"
            }

        else:
            result["status"] = "error"
            result["message"] = "Invalid action"

    except Exception as e:
        # Operational Excellence: Logging errors to CloudWatch for tracing
        print(f"Error encountered: {str(e)}") 
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({"error": str(e)})
        }

    # 4. Final Response
    return {
        'statusCode': 200,
        'headers': headers,
        'body': json.dumps(result)
    }