"use client";

import { useContext } from "react";
import { DIContext } from "../providers/DIProvider";

export const useDI = () => {
  const context = useContext(DIContext);
  if (!context) {
    throw new Error("useDI must be used within a DIProvider");
  }
  return context;
};
