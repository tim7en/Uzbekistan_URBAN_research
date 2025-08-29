"""GEE initialization and dataset availability checks."""
import ee
from typing import Dict
from .utils import DATASETS, GEE_CONFIG


def initialize_gee(project_id: str = 'ee-sabitovty') -> bool:
    try:
        print("🔑 Initializing Google Earth Engine...")
        try:
            ee.Authenticate()
            print("   ✅ Authentication successful")
        except Exception as auth_error:
            print(f"   ⚠️ Authentication skipped: {auth_error}")
        try:
            # Try initializing with provided project id first
            ee.Initialize(project=project_id)
        except Exception:
            # Try initializing without explicit project (use default credentials)
            try:
                ee.Initialize()
            except Exception as init_err:
                # Provide clearer guidance to the user depending on common failures
                err_msg = str(init_err)
                print(f"❌ GEE initialization failed: {err_msg}")
                if 'Not signed up for Earth Engine' in err_msg or 'project is not registered' in err_msg:
                    print("   ⚠️ Your Google account or GCP project is not enabled for Earth Engine.")
                    print("   Steps to resolve:")
                    print("     1) Sign up for Earth Engine: https://developers.google.com/earth-engine/guides/access")
                    print("     2) Ensure the GCP project is registered for Earth Engine and you have permission")
                    print("     3) Run: earthengine authenticate --quiet and follow browser instructions")
                    print("     4) If using a service account, set GOOGLE_APPLICATION_CREDENTIALS to the JSON key and grant it EE access")
                elif '403' in err_msg or 'PERMISSION_DENIED' in err_msg:
                    print("   ⚠️ Permission denied. Check that your account has Earth Engine access and the correct project is used.")
                    print("   You may need to: grant permissions, use a different Google account, or register the project for EE.")
                else:
                    print("   ⚠️ Unexpected initialization error. Full error shown above.")
                return False

        # Quick sanity call
        try:
            _ = ee.Image(1).getInfo()
            print("✅ GEE initialized successfully!")
            return True
        except Exception as e:
            print(f"❌ Post-initialize check failed: {e}")
            return False
    except Exception as e:
        print(f"❌ GEE initialization failed: {e}")
        return False


def gee_auth_guidance():
    """Print step-by-step guidance for resolving Earth Engine auth/permission issues."""
    print("Earth Engine authentication checklist:")
    print("  • Ensure your Google account is approved for Earth Engine (https://developers.google.com/earth-engine/guides/access)")
    print("  • Run 'earthengine authenticate' in your shell and follow the browser prompt")
    print("  • If running on a VM or service account, set GOOGLE_APPLICATION_CREDENTIALS to the service account JSON key and grant access")
    print("  • If your script uses a GCP project, ensure the project is registered for Earth Engine and your account has roles/permissions")
    print("  • For troubleshooting, try in a fresh Python REPL: import ee; ee.Authenticate(); ee.Initialize(); ee.Image(1).getInfo()")


def test_dataset_availability() -> Dict[str, bool]:
    availability = {}
    print("🔍 Testing dataset availability...")
    try:
        esri_collection = ee.ImageCollection(DATASETS['esri_lulc'])
        size = esri_collection.size().getInfo()
        availability['esri_lulc'] = size > 0
        print(f"   📊 ESRI Global LULC: {size} images available")
    except Exception as e:
        availability['esri_lulc'] = False
        print(f"   ❌ ESRI Global LULC: {e}")

    for name in ['modis_lst','landsat8','dynamic_world']:
        try:
            collection = ee.ImageCollection(DATASETS[name]).limit(1)
            size = collection.size().getInfo()
            availability[name] = size > 0
            print(f"   📊 {name}: {'✅' if size > 0 else '❌'}")
        except Exception as e:
            availability[name] = False
            print(f"   ❌ {name}: {e}")
    return availability
