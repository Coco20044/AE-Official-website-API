from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict, EmailStr, Field,model_validator
from app.models.user import UserRole

class UserCreate(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    email: EmailStr
    phone_number:str = Field(min_length=7, max_length=30)
    password: str = Field(min_length=5, max_length=128)

class UserResponse(BaseModel):
    model_config=ConfigDict(from_attributes=True)
    id: UUID
    name: str
    email:EmailStr
    phone_number:str
    role:UserRole
    is_email_verified:bool
    is_active:bool
    created_at:datetime
    updated_at:datetime
class UserLogin(BaseModel):
    email:EmailStr
    password:str=Field(min_length=1, max_length=128)
class TokenResponse(BaseModel):
    access_token:str
    token_type:str="bearer"


class UserUpdate(BaseModel):
   name: str | None = Field(
       default=None,
       min_length=2,
       max_length=150,
   )

   email: EmailStr | None = None

   phone_number: str | None = Field(
       default=None,
       min_length=7,
       max_length=30,
   )


class PasswordChange(BaseModel):
    current_password: str = Field(
        min_length=1,
        max_length=128,
    )
    new_password: str = Field(
        min_length=8,
        max_length=128,
    )
    confirm_new_password: str = Field(
        min_length=8,
        max_length=128,
    )

    @model_validator(mode="after")
    def check_passwords_match(self):
        if self.new_password != self.confirm_new_password:
            raise ValueError("New passwords do not match.")

        return self


class PasswordResetRequest(BaseModel):
    email: EmailStr

class PasswordResetConfirm(BaseModel):
  new_password: str = Field(
      min_length=8,
      max_length=120
  )
  confirm_new_password: str = Field(
      min_length=8,
      max_length=128,
  )
  @model_validator(mode="after")
  def check_passwords_match(self):
        if self.new_password != self.confirm_new_password:
            raise ValueError("New passwords do not match.")

        return self