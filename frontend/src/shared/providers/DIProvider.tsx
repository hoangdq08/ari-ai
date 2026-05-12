"use client";

import { createContext, ReactNode } from "react";
import { appDependencies, AppDependencies } from "@/core/di/di.registry";

export const DIContext = createContext<AppDependencies>(appDependencies);

export const DIProvider = ({ children, dependencies = appDependencies }: { children: ReactNode, dependencies?: AppDependencies }) => {
  return (
    <DIContext.Provider value={dependencies}>
      {children}
    </DIContext.Provider>
  );
};
