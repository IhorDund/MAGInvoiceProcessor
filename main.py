from gui import InvoiceProcessorGUI


#if __name__ == "__main__":
 #   app = InvoiceProcessorGUI()
  #  app.mainloop()

if __name__ == "__main__":
    from multiprocessing import freeze_support
    freeze_support()

    app = InvoiceProcessorGUI()
    app.mainloop()
