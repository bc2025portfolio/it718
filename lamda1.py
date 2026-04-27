import json
import boto3

s3 = boto3.client('s3')
BUCKET_NAME = "cloud-dashboard-projectbucket"

def lambda_handler(event, context):
    try:
        body = json.loads(event.get('body', '{}'))
        action = body.get('action')
        # This ID must be identical on all devices (e.g., Cognito Sub or Email)
        user_id = body.get('userId') 
        user_prefix = f"users/{user_id}/"

        if not user_id:
            return {"statusCode": 400, "body": json.dumps("User Identity Missing")}

        # --- SYNC: LIST CURRENT PROJECTS ---
        if action == "LIST_FILES":
            response = s3.list_objects_v2(Bucket=BUCKET_NAME, Prefix=user_prefix)
            files = []
            if 'Contents' in response:
                # Sort by newest so all devices see the same order
                sorted_objs = sorted(response['Contents'], key=lambda x: x['LastModified'], reverse=True)
                for obj in sorted_objs[:5]:
                    files.append({
                        "name": obj['Key'].replace(user_prefix, ""),
                        "size": round(obj['Size'] / 1024, 2)
                    })
            return {"statusCode": 200, "body": json.dumps({"projects": files})}

        # --- UPLOAD: ENFORCE 5-SLOT LIMIT ---
        elif action == "PROCESS_UPLOAD":
            # First, check how many projects exist in the "middle ground"
            current = s3.list_objects_v2(Bucket=BUCKET_NAME, Prefix=user_prefix)
            count = current.get('KeyCount', 0)
            
            if count >= 5:
                return {"statusCode": 400, "body": json.dumps({"error": "S3 Storage Full (5 Projects Max)"})}

            file_name = body.get('fileName')
            import base64
            content = base64.b64decode(body.get('fileContent'))
            
            s3.put_object(Bucket=BUCKET_NAME, Key=f"{user_prefix}{file_name}", Body=content)
            return {"statusCode": 200, "body": json.dumps({"status": "Uploaded to Cloud"})}

    except Exception as e:
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}