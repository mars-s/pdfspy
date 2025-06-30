interface ComprehensiveSDSData {
  identification: {
    productName: string;
    productCode: string;
    version: string;
  };
  hazardClassification: {
    signalWord: string;
    hazardStatements: string[];
  };
  ingredients: {
    component: string;
    CAS: string;
    REACH_registration_number: string;
    concentration: string;
  }[];
}
