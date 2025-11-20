from datetime import datetime, timedelta

from azure.storage.blob import BlobSasPermissions, BlobServiceClient, generate_blob_sas
from app.core.conf import settings


def get_blob_service_client():
    """
    Lazily create a BlobServiceClient.
    This avoids import-time errors in tests with fake connection strings.
    """
    return BlobServiceClient.from_connection_string(settings.ADLS_CONNECTION_STRING)


def generate_sas_url(blob_path: str, expiry_minutes: int = 60, isUpload=False) -> str:
    client = get_blob_service_client()

    # account_key might be None if using a connection string with a SAS token
    account_key = getattr(client.credential, "account_key", None)
    if not account_key:
        raise ValueError(
            "BlobServiceClient missing account key; cannot generate SAS URL."
        )

    sas_token = generate_blob_sas(
        account_name=client.account_name,
        container_name=settings.ADLS_CONTAINER_NAME,
        blob_name=blob_path,
        account_key=account_key,
        permission=(
            BlobSasPermissions(read=True)
            if not isUpload
            else BlobSasPermissions(write=True, create=True)
        ),
        expiry=datetime.utcnow() + timedelta(minutes=expiry_minutes),
    )
    url = f"https://{client.account_name}.blob.core.windows.net/{settings.ADLS_CONTAINER_NAME}/{blob_path}?{sas_token}"
    return url


def upload_to_blob(blob_name: str, file_obj):
    client = get_blob_service_client()
    container_client = client.get_container_client(settings.ADLS_CONTAINER_NAME)
    blob_client = container_client.get_blob_client(blob_name)
    blob_client.upload_blob(file_obj, overwrite=True)
