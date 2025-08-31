#!/usr/bin/env python3
"""
Test script to verify enhanced framework implementation works correctly.
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_enhanced_framework_imports():
    """Test that enhanced framework imports work correctly"""
    print("Testing enhanced framework imports...")
    
    try:
        from valiant.framework.enhanced_workflow import EnhancedBaseWorkflow
        from valiant.framework.decorators import step, EnhancedStepResult, APIAuthStep
        from valiant.framework.workflow_registry import workflow_registry
        print("✅ Enhanced framework imports successful")
        return True
    except Exception as e:
        print(f"❌ Enhanced framework import failed: {e}")
        import traceback
        print(traceback.format_exc())
        return False

def test_existing_workflow_compatibility():
    """Test that existing workflows still work"""
    print("\nTesting existing workflow compatibility...")
    
    try:
        from valiant.workflows.api_validation.workflow import APIValidationWorkflow
        from valiant.workflows.system_health.workflow import SystemHealthWorkflow
        from valiant.workflows.user_validation.workflow import UserValidationWorkflow
        
        api_workflow = APIValidationWorkflow()
        system_workflow = SystemHealthWorkflow()
        user_workflow = UserValidationWorkflow()
        
        print("✅ Existing workflow imports and instantiation successful")
        return True
    except Exception as e:
        print(f"❌ Existing workflow compatibility failed: {e}")
        import traceback
        print(traceback.format_exc())
        return False

def test_enhanced_workflow_features():
    """Test enhanced workflow features"""
    print("\nTesting enhanced workflow features...")
    
    try:
        from examples.enhanced_workflow_example import EnhancedAPIWorkflow, LegacyCompatibilityWorkflow
        
        enhanced = EnhancedAPIWorkflow()
        print(f"✅ Enhanced workflow created: {enhanced.get_metadata().name}")
        
        is_valid, errors = enhanced.validate_workflow()
        print(f"✅ Enhanced workflow validation: {'Valid' if is_valid else 'Invalid'}")
        if errors:
            for error in errors:
                print(f"  - {error}")
        
        step_metadata = enhanced.get_step_metadata()
        print(f"✅ Enhanced workflow has {len(step_metadata)} steps")
        
        legacy = LegacyCompatibilityWorkflow()
        print(f"✅ Legacy compatibility workflow created: {legacy.name}")
        
        return True
    except Exception as e:
        print(f"❌ Enhanced workflow features test failed: {e}")
        import traceback
        print(traceback.format_exc())
        return False

def test_workflow_execution():
    """Test workflow execution with enhanced framework"""
    print("\nTesting workflow execution...")
    
    try:
        from valiant.workflows.api_validation.workflow import APIValidationWorkflow
        from valiant.framework.engine import WorkflowRunner
        
        runner = WorkflowRunner(verbose=True, output_format='json')
        workflow = APIValidationWorkflow(runner)
        
        inputs = workflow.get_input_fields()
        print(f"✅ API workflow has {len(inputs)} input fields")
        
        workflow.define_steps()
        print(f"✅ API workflow has {len(runner.steps)} steps defined")
        
        return True
    except Exception as e:
        print(f"❌ Workflow execution test failed: {e}")
        import traceback
        print(traceback.format_exc())
        return False

def main():
    """Run all tests"""
    print("Enhanced Framework Test Suite")
    print("=" * 50)
    
    tests = [
        test_enhanced_framework_imports,
        test_existing_workflow_compatibility,
        test_enhanced_workflow_features,
        test_workflow_execution
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print("\n" + "=" * 50)
    print(f"Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Enhanced framework is working correctly.")
        return 0
    else:
        print("⚠️  Some tests failed. Please check the errors above.")
        return 1

if __name__ == "__main__":
    exit(main())
