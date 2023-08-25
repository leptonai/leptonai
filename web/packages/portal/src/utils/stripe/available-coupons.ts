const AvailableCoupons: {
  [key: string]: Record<"test" | "prod", string>;
} = {
  "10": {
    test: "XqK2kAkF",
    prod: "2H4gOON2",
  },
  "100": {
    test: "4xRmxX5x",
    prod: "utZdepf7",
  },
  "500": {
    test: "LvDu60Lr",
    prod: "l87mbyMZ",
  },
  "1000": {
    test: "PdTZ9Apj",
    prod: "XOcOs9Pg",
  },
};

export const getAvailableCoupons = (
  discount: keyof typeof AvailableCoupons,
  chargeable: boolean
): string => {
  const targetCoupon = AvailableCoupons[discount];
  return chargeable ? targetCoupon.prod : targetCoupon.test;
};
