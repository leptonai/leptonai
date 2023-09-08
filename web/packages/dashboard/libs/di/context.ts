import { createContext } from "react";
import { Injector } from "injection-js";

export const InjectorContext = createContext<Injector>(Injector.NULL);
