from pydantic import BaseModel, EmailStr
from typing import Optional
from fastapi import APIRouter
from auth.supabase_client import supabase
from routers.auth import get_current_user
from fastapi import UploadFile, File, Depends, HTTPException
import uuid


router = APIRouter(tags=["Profile"])

class UpdateProfileRequest(BaseModel):
    name: Optional[str] = None
    avatar_url: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = None



@router.patch("/profile")
def update_profile(
    payload: UpdateProfileRequest,
    user=Depends(get_current_user)
):
    user_id = user.id
    if payload.email or payload.password:
        try:
            update_data = {}
            if payload.email:
                update_data["email"] = payload.email
            if payload.password:
                update_data["password"] = payload.password

            supabase.auth.admin.update_user_by_id(user_id, update_data)
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    profile_data = {}

    if payload.name is not None:
        profile_data["name"] = payload.name

    if profile_data:
        supabase.table("profiles") \
            .update(profile_data) \
            .eq("id", user_id) \
            .execute()

    return {"message": "Profile updated"}


@router.post("/profile/avatar")
async def upload_avatar(
    file: UploadFile = File(...),
    user=Depends(get_current_user)
):
    user_id = user.id

    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is missing")

    if file.content_type not in ["image/png", "image/jpeg", "image/jpg"]:
        raise HTTPException(status_code=400, detail="Invalid image type")

    print("UPLOAD AVATAR")
    print("Filename:", file.filename)
    print("Content-Type:", file.content_type)

    file_ext = file.filename.split(".")[-1]
    file_name = f"{user_id}/{uuid.uuid4()}.{file_ext}"

    try:
        file_bytes = await file.read()

        supabase.storage.from_("Avatar").upload(
            file_name,
            file_bytes,
            file_options={
                "content-type": file.content_type,
                "upsert": "true"   # ✅ FIX DI SINI
            }
        )

        public_url = supabase.storage.from_("Avatar").get_public_url(file_name)["publicUrl"]

        supabase.table("profiles") \
            .update({"avatar_url": public_url}) \
            .eq("id", user_id) \
            .execute()

        return {"avatar_url": public_url}

    except Exception as e:
        print("UPLOAD ERROR:", str(e))
        raise HTTPException(status_code=400, detail=str(e))