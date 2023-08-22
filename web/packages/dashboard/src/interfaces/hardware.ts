export type Hardware = {
  [key: string]: {
    Description: string;
    DisplayName: string;
    Selectable: boolean;
    Resource: {
      EphemeralStorageInGB: number;
      Memory: number;
      CPU: number;
      AcceleratorType?: string;
      AcceleratorNum?: number;
    };
  };
};
