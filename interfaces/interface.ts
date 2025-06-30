interface SDSData {
  productName: string;
  hazard: {
    signalWord: string;
    hazardStatements: string[];
  };
  substances: {
    component: string;
    CAS: string;
    REACH_registration_number: string;
  }[];
}
