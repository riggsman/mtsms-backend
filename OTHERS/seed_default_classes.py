"""
Seed script to populate default classes for Higher Institution (HI) and Secondary Institution (SI)
Run this script after migrations to populate default classes for each tenant.
"""
import sys
from sqlalchemy.orm import Session
from app.database.sessionManager import get_db_session
from app.models.classes import Class
from app.models.tenant import Tenant

# Default classes for Higher Institution (HI)
HI_DEFAULT_CLASSES = [
    {"name": "Level 1", "code": "L1", "institution_level": "HI"},
    {"name": "Level 2", "code": "L2", "institution_level": "HI"},
    {"name": "Level 3", "code": "L3", "institution_level": "HI"},
    {"name": "Level 4", "code": "L4", "institution_level": "HI"},
    {"name": "Level 5", "code": "L5", "institution_level": "HI"},
]

# Default classes for Secondary Institution (SI)
SI_DEFAULT_CLASSES = [
    {"name": "Grade 7", "code": "G7", "institution_level": "SI"},
    {"name": "Grade 8", "code": "G8", "institution_level": "SI"},
    {"name": "Grade 9", "code": "G9", "institution_level": "SI"},
    {"name": "Grade 10", "code": "G10", "institution_level": "SI"},
    {"name": "Grade 11", "code": "G11", "institution_level": "SI"},
    {"name": "Grade 12", "code": "G12", "institution_level": "SI"},
]

def seed_default_classes():
    """Seed default classes for all existing tenants"""
    db: Session = get_db_session()
    
    try:
        # Get all tenants
        tenants = db.query(Tenant).all()
        
        if not tenants:
            print("No tenants found. Please create a tenant first.")
            return
        
        total_created = 0
        
        for tenant in tenants:
            print(f"\nProcessing tenant: {tenant.name} (ID: {tenant.id})")
            
            # Check if classes already exist for this tenant
            existing_classes = db.query(Class).filter(
                Class.institution_id == tenant.id,
                Class.deleted_at.is_(None)
            ).all()
            
            if existing_classes:
                print(f"  Tenant already has {len(existing_classes)} classes. Skipping...")
                continue
            
            # Create HI classes
            for class_data in HI_DEFAULT_CLASSES:
                new_class = Class(
                    institution_id=tenant.id,
                    name=class_data["name"],
                    code=class_data["code"],
                    institution_level=class_data["institution_level"]
                )
                db.add(new_class)
                total_created += 1
                print(f"  Created: {class_data['name']} ({class_data['code']}) - {class_data['institution_level']}")
            
            # Create SI classes
            for class_data in SI_DEFAULT_CLASSES:
                new_class = Class(
                    institution_id=tenant.id,
                    name=class_data["name"],
                    code=class_data["code"],
                    institution_level=class_data["institution_level"]
                )
                db.add(new_class)
                total_created += 1
                print(f"  Created: {class_data['name']} ({class_data['code']}) - {class_data['institution_level']}")
        
        db.commit()
        print(f"\n✅ Successfully created {total_created} default classes for {len(tenants)} tenant(s).")
        
    except Exception as e:
        db.rollback()
        print(f"\n❌ Error seeding default classes: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    print("Starting default classes seed...")
    seed_default_classes()
    print("\nSeed completed!")
