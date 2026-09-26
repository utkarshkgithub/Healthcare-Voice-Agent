from pydantic import BaseModel
from typing import Optional

class LoginRequest(BaseModel):
    email: str
    password: str

class AppointmentRequest(BaseModel):
    patient_id: int
    doctor_id: int
    slot_id: int
    reason: str
    payment_id: Optional[str] = None

class PatientDetailsResponse(BaseModel):
    # Demographic fields are genuinely nullable — a patient may not have
    # supplied a blood group or marital status. Declaring these as plain str
    # made the response model reject real rows and turn them into a 500.
    name: str
    date_of_birth: Optional[str] = None
    gender: Optional[str] = None
    contact_number: Optional[str] = None
    medical_record_number: Optional[str] = None
    blood_group: Optional[str] = None
    marital_status: Optional[str] = None
    id: int

class MedicalHistoryResponse(BaseModel):
    past_diagnoses: Optional[str] = None
    surgeries: Optional[str] = None
    hospital_admissions: Optional[str] = None
    immunization_records: Optional[str] = None
    family_medical_history: Optional[str] = None
    lifestyle_factors: Optional[str] = None