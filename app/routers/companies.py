from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from datetime import datetime

from app.core.security import get_password_hash
from app.database.session import get_session
from app.models.company import Company, CompanyRecruiterLink
from app.models.user import User
from app.dependencies.auth import get_current_user
from app.schemas.company import (
    AddRecruiterRequest,
    CompanyCreateRequest,
    CompanyUpdateRequest,
    CompanyResponse
)

router = APIRouter(
    prefix="/companies",
    tags=["Companies"]
)


@router.post(
    "",
    response_model=CompanyResponse,
    status_code=status.HTTP_201_CREATED
)
def create_company(
    data: CompanyCreateRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new company profile.

    **Permissions:**
    - Only users with the role 'recruiter' can create companies.

    **Business Logic:**
    - Verifies that a company with the same name does not already exist to prevent duplicates.
    - Associates the created company with the logged-in recruiter.

    **Args:**
    - data (CompanyCreateRequest): Name, description, website, and location.

    **Returns:**
    - CompanyResponse: The created company object.

    **Raises:**
    - 403 Forbidden: If the user is not a recruiter.
    - 400 Bad Request: If a company with the given name already exists.
    """
    
    # Authorization Check: Ensure user has the correct role
    if current_user.role != "recruiter":
        raise HTTPException(
            status_code=403,
            detail="Only recruiters can create companies"
        )
    
    # Validation: Check for duplicate company names
    if data.name:
        existing_company = session.exec(
            select(Company).where(Company.name == data.name)
        ).first()

        if existing_company:
            raise HTTPException(
                status_code=400,
                detail="Company with this name already exists"
            )

    # Creation: Instantiate the model
    # Note: recruiter_id is automatically pulled from the authenticated user
    company = Company(
        name=data.name,
        description=data.description,
        website=data.website,
        location=data.location,
        recruiter_id=current_user.id,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )

    session.add(company)
    session.commit()
    session.refresh(company)

    return company


@router.get(
    "",
    response_model=list[CompanyResponse],
    status_code=status.HTTP_200_OK
)
def list_companies(
    session: Session = Depends(get_session)
):
    """
    Retrieve a list of all registered companies.

    **Permissions:**
    - Public access (no authentication required).

    **Returns:**
    - list[CompanyResponse]: A list of all company objects.
    """
    return session.exec(select(Company)).all()


@router.get(
    "/{company_id}",
    response_model=CompanyResponse,
    status_code=status.HTTP_200_OK
)
def get_company(
    company_id: int,
    session: Session = Depends(get_session)
):
    """
    Retrieve details for a specific company by ID.

    **Args:**
    - company_id (int): The unique identifier of the company.

    **Returns:**
    - CompanyResponse: The company object.

    **Raises:**
    - 404 Not Found: If the company ID does not exist.
    """
    company = session.get(Company, company_id)

    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    return company


@router.put(
    "/{company_id}",
    response_model=CompanyResponse,
    status_code=status.HTTP_200_OK
)
def update_company(
    company_id: int,
    data: CompanyUpdateRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Update an existing company's details.

    **Permissions:**
    - Only the recruiter who created the company (the owner) can update it.

    **Args:**
    - company_id (int): ID of the company to update.
    - data (CompanyUpdateRequest): Fields to update (partial updates allowed).

    **Returns:**
    - CompanyResponse: The updated company object.

    **Raises:**
    - 404 Not Found: If the company does not exist.
    - 403 Forbidden: If the logged-in user is not the owner of the company.
    """
    
    # Check if company exists
    company = session.get(Company, company_id)

    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    # Authorization Check: Ownership
    if company.recruiter_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Not authorized to update this company"
        )

    # Partial Update: Only update fields that were actually sent in the request
    for field, value in data.dict(exclude_unset=True).items():
        setattr(company, field, value)

    # Update timestamp
    company.updated_at = datetime.utcnow()
    
    session.add(company)
    session.commit()
    session.refresh(company)

    return company


@router.delete("/{company_id}")
def delete_company(
    company_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a company profile.

    **Permissions:**
    - Only the recruiter who created the company (the owner) can delete it.

    **Args:**
    - company_id (int): ID of the company to delete.

    **Returns:**
    - dict: A success message.

    **Raises:**
    - 404 Not Found: If the company does not exist.
    - 403 Forbidden: If the logged-in user is not the owner.
    """
    
    # Check if company exists
    company = session.get(Company, company_id)

    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    # Authorization Check: Ownership
    if company.recruiter_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Not authorized to delete this company"
        )

    session.delete(company)
    session.commit()

    return {"detail": "Company deleted successfully"}

@router.post("/{company_id}/add_recruiter", status_code=status.HTTP_200_OK)
def add_recruiter_to_company(
    company_id: int,
    data: AddRecruiterRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Add a recruiter to a company profile.

    **Permissions:**
    - Only the owner recruiter of the company can add another recruiter.

    **Args:**
    - company_id (int): ID of the company.
    - data (AddRecruiterRequest): Email of the recruiter to add.

    **Returns:**
    - dict: Success message.

    **Raises:**
    - 404 Not Found: If the company or recruiter does not exist.
    - 403 Forbidden: If the logged-in user is not the owner of the company.
    """
    
    # Check if company exists
    company = session.get(Company, company_id)

    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    # Authorization Check: Ownership
    if company.recruiter_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Not authorized to add recruiters to this company"
        )

    # Find the recruiter by email
    recruiter = session.exec(
        select(User).where(User.email == data.email, User.role == "recruiter")
    ).first()

    if not recruiter:
        if not data.password or not data.name:
            raise HTTPException(
                status_code=404,
                detail="Recruiter not found. To create a new recruiter, please provide password."
            )
        # Create a new recruiter if not found
        recruiter = User(
            email=data.email,
            hashed_password=get_password_hash(data.password),
            role="recruiter",
            name=data.name,
            is_active=True,
            created_at=datetime.utcnow()
        )
        session.add(recruiter)
        session.commit()
        session.refresh(recruiter)

        message = f"Recruiter {data.email} created and added to company successfully."
    else:
        if recruiter.role != "recruiter":
            raise HTTPException(
                status_code=400,
                detail="The specified user is not a recruiter."
            )
        
        message = f"Recruiter {data.email} added to company successfully."                  
   
    existing_link = session.exec(
        select(CompanyRecruiterLink).where(
            CompanyRecruiterLink.company_id == company_id,
            CompanyRecruiterLink.recruiter_id == recruiter.id
        )
    ).first()

    if existing_link or company.recruiter_id == recruiter.id:
       return {"detail": f"Recruiter {data.email} is already associated with the company."}

    link = CompanyRecruiterLink(
        company_id=company_id,
        recruiter_id=recruiter.id
    )
    session.add(link)
    session.commit()

    return {"message": message,"user_email": recruiter.email,"company_name": company.name}

@router.get("/{company_id}/recruiters", status_code=status.HTTP_200_OK)
def list_company_recruiters(
    company_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    List all recruiters associated with a company.

    **Permissions:**
    - Only the owner recruiter of the company can view the list.

    **Args:**
    - company_id (int): ID of the company.

    **Returns:**
    - list[dict]: List of recruiters associated with the company.

    **Raises:**
    - 404 Not Found: If the company does not exist.
    - 403 Forbidden: If the logged-in user is not the owner of the company.
    """
    
    # Check if company exists
    company = session.get(Company, company_id)

    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    # Authorization Check: Ownership
    if company.recruiter_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Not authorized to view recruiters of this company"
        )

    # Query associated recruiters
    links = session.exec(
        select(CompanyRecruiterLink).where(CompanyRecruiterLink.company_id == company_id)
    ).all()

    recruiter_ids = [link.recruiter_id for link in links]
    recruiter_ids.append(company.recruiter_id)  # Include owner recruiter

    recruiters = session.exec(
        select(User).where(getattr(User, "id").in_(recruiter_ids))
    ).all()

    return [{"id": r.id, "email": r.email} for r in recruiters]