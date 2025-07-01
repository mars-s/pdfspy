interface ProductInfo {
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
}
