#!/usr/bin/env python3
"""
Test Runner Script for PDF Scrapper
Provides various test execution options and reporting
"""

import sys
import os
import subprocess
import argparse
import json
import time
from datetime import datetime
from pathlib import Path

class TestRunner:
    """Main test runner class"""
    
    def __init__(self):
        self.test_results = {}
        self.start_time = None
        self.end_time = None
    
    def run_basic_tests(self):
        """Run basic functionality tests"""
        print("🧪 Running Basic Tests...")
        cmd = ["python", "-m", "pytest", "test_pdf_scrapper.py::TestInterfaceVariations", "-v"]
        return self._run_pytest_command(cmd, "basic_tests")
    
    def run_performance_tests(self):
        """Run performance tests"""
        print("⚡ Running Performance Tests...")
        cmd = ["python", "-m", "pytest", "test_performance_edge_cases.py", "-m", "performance", "-v"]
        return self._run_pytest_command(cmd, "performance_tests")
    
    def run_edge_case_tests(self):
        """Run edge case tests"""
        print("🔍 Running Edge Case Tests...")
        cmd = ["python", "-m", "pytest", "test_performance_edge_cases.py::TestEdgeCasesAndErrorHandling", "-v"]
        return self._run_pytest_command(cmd, "edge_case_tests")
    
    def run_consistency_tests(self):
        """Run consistency and determinism tests"""
        print("🔄 Running Consistency Tests...")
        cmd = ["python", "-m", "pytest", "test_pdf_scrapper.py::TestConsistencyAndDeterminism", "-v"]
        return self._run_pytest_command(cmd, "consistency_tests")
    
    def run_all_tests(self):
        """Run all tests"""
        print("🚀 Running All Tests...")
        cmd = ["python", "-m", "pytest", "-v", "--tb=short"]
        return self._run_pytest_command(cmd, "all_tests")
    
    def run_smoke_tests(self):
        """Run quick smoke tests"""
        print("💨 Running Smoke Tests...")
        cmd = ["python", "-m", "pytest", "-v", "-x", "--tb=line", 
               "test_pdf_scrapper.py::TestInterfaceVariations::test_original_interface"]
        return self._run_pytest_command(cmd, "smoke_tests")
    
    def run_interface_variation_tests(self):
        """Run tests for different interface variations"""
        print("🔧 Running Interface Variation Tests...")
        cmd = ["python", "-m", "pytest", "test_performance_edge_cases.py::TestInterfaceVariationsExtensive", "-v"]
        return self._run_pytest_command(cmd, "interface_variation_tests")
    
    def _run_pytest_command(self, cmd, test_type):
        """Run a pytest command and capture results"""
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            self.test_results[test_type] = {
                "return_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "success": result.returncode == 0
            }
            
            if result.returncode == 0:
                print(f"✅ {test_type} passed")
            else:
                print(f"❌ {test_type} failed")
                print(f"Error output: {result.stderr}")
            
            return result.returncode == 0
            
        except subprocess.TimeoutExpired:
            print(f"⏰ {test_type} timed out")
            self.test_results[test_type] = {
                "return_code": -1,
                "error": "Test timed out",
                "success": False
            }
            return False
        except Exception as e:
            print(f"💥 {test_type} crashed: {e}")
            self.test_results[test_type] = {
                "return_code": -1,
                "error": str(e),
                "success": False
            }
            return False
    
    def generate_report(self):
        """Generate a test report"""
        print("\n" + "="*60)
        print("📊 TEST EXECUTION REPORT")
        print("="*60)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results.values() if result["success"])
        failed_tests = total_tests - passed_tests
        
        print(f"Total Test Suites: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {failed_tests}")
        
        if self.start_time and self.end_time:
            duration = self.end_time - self.start_time
            print(f"Total Duration: {duration:.2f} seconds")
        
        print("\nDetailed Results:")
        for test_type, result in self.test_results.items():
            status = "✅ PASS" if result["success"] else "❌ FAIL"
            print(f"  {test_type}: {status}")
            
            if not result["success"] and "error" in result:
                print(f"    Error: {result['error']}")
        
        # Save detailed report to file
        report_data = {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total": total_tests,
                "passed": passed_tests,
                "failed": failed_tests,
                "success_rate": (passed_tests / total_tests * 100) if total_tests > 0 else 0
            },
            "results": self.test_results
        }
        
        with open("test_report.json", "w") as f:
            json.dump(report_data, f, indent=2)
        
        print(f"\n📄 Detailed report saved to: test_report.json")
        
        return failed_tests == 0

def create_test_files():
    """Create sample test files if they don't exist"""
    sample_files = {
        "sample.pdf": "Sample PDF file needed for testing",
        "interface.ts": """interface SDSData {
  productName: string;
  hazard: {
    signalWord: string;
    hazardStatements: string[];
  };
  ingredients: {
    chemicalName: string;
    casNumber: string;
    weightPercent: string;
  }[];
}""",
        # Add any other required files
    }
    
    for filename, content in sample_files.items():
        if not os.path.exists(filename):
            print(f"⚠️  Warning: {filename} not found. Creating placeholder...")
            if filename.endswith('.ts'):
                with open(filename, 'w') as f:
                    f.write(content)
            else:
                print(f"   Please ensure {filename} exists for full testing")

def main():
    """Main function to run tests based on command line arguments"""
    parser = argparse.ArgumentParser(description="PDF Scrapper Test Runner")
    parser.add_argument("--test-type", 
                       choices=["basic", "performance", "edge-cases", "consistency", 
                               "smoke", "interface-variations", "all"],
                       default="smoke",
                       help="Type of tests to run")
    parser.add_argument("--create-files", action="store_true",
                       help="Create sample test files")
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Verbose output")
    parser.add_argument("--generate-coverage", action="store_true",
                       help="Generate code coverage report")
    
    args = parser.parse_args()
    
    # Create test files if requested
    if args.create_files:
        create_test_files()
        return
    
    # Initialize test runner
    runner = TestRunner()
    runner.start_time = time.time()
    
    print("🏁 Starting PDF Scrapper Test Suite")
    print(f"⏰ Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Check if required files exist
    required_files = ["main.py"]  # Add other required files
    missing_files = [f for f in required_files if not os.path.exists(f)]
    
    if missing_files:
        print(f"❌ Missing required files: {missing_files}")
        print("Please ensure all required files are present before running tests")
        return 1
    
    # Run appropriate tests
    success = True
    
    if args.test_type == "basic":
        success = runner.run_basic_tests()
    elif args.test_type == "performance":
        success = runner.run_performance_tests()
    elif args.test_type == "edge-cases":
        success = runner.run_edge_case_tests()
    elif args.test_type == "consistency":
        success = runner.run_consistency_tests()
    elif args.test_type == "smoke":
        success = runner.run_smoke_tests()
    elif args.test_type == "interface-variations":
        success = runner.run_interface_variation_tests()
    elif args.test_type == "all":
        # Run all test categories
        test_methods = [
            runner.run_smoke_tests,
            runner.run_basic_tests,
            runner.run_consistency_tests,
            runner.run_edge_case_tests,
            runner.run_interface_variation_tests,
            runner.run_performance_tests,  # Run performance tests last
        ]
        
        success = True
        for test_method in test_methods:
            if not test_method():
                success = False
                # Continue running other tests even if one fails
    
    runner.end_time = time.time()
    
    # Generate coverage report if requested
    if args.generate_coverage:
        print("\n📈 Generating Coverage Report...")
        try:
            subprocess.run(["python", "-m", "pytest", "--cov=main", "--cov-report=html"], 
                          capture_output=True, text=True)
            print("📊 Coverage report generated in htmlcov/")
        except Exception as e:
            print(f"⚠️  Could not generate coverage report: {e}")
    
    # Generate final report
    overall_success = runner.generate_report()
    
    if overall_success:
        print("\n🎉 All tests completed successfully!")
        return 0
    else:
        print("\n😞 Some tests failed. Check the report for details.")
        return 1

if __name__ == "__main__":
    sys.exit(main())