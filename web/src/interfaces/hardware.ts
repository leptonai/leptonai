export type Hardware = {
  [key: string]: {
    Description: string;
    DisplayName: string;
    Resource: {
      EphemeralStorageInGB: number;
      Memory: number;
      CPU: number;
      AcceleratorType?: string;
      AcceleratorNum?: string;
    };
  };
};
