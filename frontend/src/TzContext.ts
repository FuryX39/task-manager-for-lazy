import { createContext, useContext } from "react";

export const TzContext = createContext<string>("UTC");

export function useTz(): string {
  return useContext(TzContext);
}
