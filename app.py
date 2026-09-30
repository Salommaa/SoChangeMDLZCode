import pandas as pd
import streamlit as st
import zipfile
import io


# --------------------------------------------------
# Page Configuration
# --------------------------------------------------

st.set_page_config(
    page_title="SO Handling Tool",
    page_icon="📁",
    layout="wide"
)


# --------------------------------------------------
# Title
# --------------------------------------------------

st.title("SO Handling Tool")

st.write(
    "Upload the PPL file and SO folder. "
    "The tool will identify Link Codes starting with 4 "
    "and replace them using the MDLZ Code → RETC Code mapping."
)


# --------------------------------------------------
# Upload PPL
# --------------------------------------------------

ppl_file = st.file_uploader(
    "Upload The PPL File as Excel",
    type=["xlsx", "xls"]
)

ppl_data = None


if ppl_file is not None:

    try:

        ppl_data = pd.read_excel(ppl_file)

        # Clean column names
        ppl_data.columns = ppl_data.columns.str.strip()

        # Check required columns
        required_columns = [
            "MDLZ code",
            "RETC code"
        ]

        missing_columns = [
            col
            for col in required_columns
            if col not in ppl_data.columns
        ]

        if missing_columns:

            st.error(
                "The PPL file is missing the following columns: "
                + ", ".join(missing_columns)
            )

            ppl_data = None

        else:

            st.success(
                "PPL file uploaded successfully!"
            )

    except Exception as e:

        st.error(
            f"Error reading PPL file: {e}"
        )

        ppl_data = None


# --------------------------------------------------
# Upload SO Folder
# --------------------------------------------------

so_folder = st.file_uploader(
    "Upload SO Folder",
    type=["csv"],
    accept_multiple_files="directory"
)


if so_folder:

    st.success(
        f"{len(so_folder)} SO files uploaded successfully!"
    )

    # Show uploaded files
    with st.expander("Show Uploaded SO Files"):

        for file in so_folder:
            st.write(file.name)


# --------------------------------------------------
# Proceed
# --------------------------------------------------

if ppl_data is not None and so_folder:

    proceed = st.button(
        "Proceed",
        type="primary"
    )


    if proceed:

        # --------------------------------------------------
        # Clean PPL codes
        # --------------------------------------------------

        ppl_data["MDLZ code"] = (
            ppl_data["MDLZ code"]
            .astype(str)
            .str.strip()
            .str.replace(r"\.0$", "", regex=True)
        )

        ppl_data["RETC code"] = (
            ppl_data["RETC code"]
            .astype(str)
            .str.strip()
            .str.replace(r"\.0$", "", regex=True)
        )


        # --------------------------------------------------
        # Create Lookup
        #
        # MDLZ code -> RETC code
        # --------------------------------------------------

        lookup = dict(
            zip(
                ppl_data["MDLZ code"],
                ppl_data["RETC code"]
            )
        )


        # --------------------------------------------------
        # Counters
        # --------------------------------------------------

        total_updated_rows = 0
        total_target_rows = 0

        all_target_codes = set()

        file_results = []


        # --------------------------------------------------
        # Create ZIP in Memory
        # --------------------------------------------------

        zip_buffer = io.BytesIO()


        with zipfile.ZipFile(
            zip_buffer,
            "w",
            zipfile.ZIP_DEFLATED
        ) as zip_file:


            # --------------------------------------------------
            # Process Every SO File
            # --------------------------------------------------

            for file in so_folder:

                try:

                    # ------------------------------------------
                    # Read CSV
                    # ------------------------------------------

                    df = pd.read_csv(
                        file,
                        low_memory=False
                    )


                    # ------------------------------------------
                    # Check Link Code Column
                    # ------------------------------------------

                    if "Link Code" not in df.columns:

                        # Keep the file in the ZIP
                        # even if it has no Link Code column

                        csv_data = df.to_csv(
                            index=False
                        ).encode("utf-8-sig")


                        zip_file.writestr(
                            file.name,
                            csv_data
                        )


                        file_results.append({
                            "File": file.name,
                            "Target Rows": 0,
                            "Unique Target Codes": 0,
                            "Updated Rows": 0,
                            "Status": "No Link Code Column"
                        })


                        continue


                    # --------------------------------------------------
                    # Keep Original Link Code
                    # --------------------------------------------------

                    original_link_code = (
                        df["Link Code"]
                        .astype(str)
                        .str.strip()
                        .str.replace(
                            r"\.0$",
                            "",
                            regex=True
                        )
                    )


                    df["Link Code"] = original_link_code


                    # --------------------------------------------------
                    # Find Link Codes Starting With 4
                    #
                    # These become target_codes
                    # --------------------------------------------------

                    target_mask = (
                        df["Link Code"]
                        .str.startswith(
                            "4",
                            na=False
                        )
                    )


                    target_codes = set(
                        df.loc[
                            target_mask,
                            "Link Code"
                        ]
                    )


                    # Keep targets found across all SO files
                    all_target_codes.update(
                        target_codes
                    )


                    # Number of ROWS starting with 4
                    target_rows = int(
                        target_mask.sum()
                    )


                    total_target_rows += (
                        target_rows
                    )


                    # --------------------------------------------------
                    # Replace From PPL
                    #
                    # Same logic as:
                    #
                    # lookup.get(x, x)
                    #
                    # If found:
                    #     Replace with RETC
                    #
                    # If not found:
                    #     Keep original
                    # --------------------------------------------------

                    df["Link Code"] = (
                        original_link_code.apply(
                            lambda x:
                            lookup.get(x, x)
                            if x in target_codes
                            else x
                        )
                    )


                    # --------------------------------------------------
                    # Count ONLY Rows That Actually Changed
                    # --------------------------------------------------

                    updated_rows = int(
                        (
                            df["Link Code"]
                            != original_link_code
                        ).sum()
                    )


                    total_updated_rows += (
                        updated_rows
                    )


                    # --------------------------------------------------
                    # Add File to ZIP
                    #
                    # Even if updated_rows = 0,
                    # file is still included.
                    # --------------------------------------------------

                    csv_data = df.to_csv(
                        index=False
                    ).encode("utf-8-sig")


                    zip_file.writestr(
                        file.name,
                        csv_data
                    )


                    # --------------------------------------------------
                    # File Analysis
                    # --------------------------------------------------

                    file_results.append({

                        "File":
                            file.name,

                        "Target Rows":
                            target_rows,

                        "Unique Target Codes":
                            len(target_codes),

                        "Updated Rows":
                            updated_rows,

                        "Status":
                            (
                                "Updated"
                                if updated_rows > 0
                                else "No Update"
                            )
                    })


                except Exception as e:

                    # --------------------------------------------------
                    # If Processing Fails
                    #
                    # Put ORIGINAL file into ZIP
                    # --------------------------------------------------

                    try:

                        file.seek(0)

                        zip_file.writestr(
                            file.name,
                            file.read()
                        )

                    except Exception:
                        pass


                    file_results.append({

                        "File":
                            file.name,

                        "Target Rows":
                            0,

                        "Unique Target Codes":
                            0,

                        "Updated Rows":
                            0,

                        "Status":
                            f"Error: {e}"
                    })


        # --------------------------------------------------
        # Finish ZIP
        # --------------------------------------------------

        zip_buffer.seek(0)


        # --------------------------------------------------
        # Results
        # --------------------------------------------------

        st.success(
            "Processing completed successfully!"
        )


        st.divider()


        # --------------------------------------------------
        # Summary
        # --------------------------------------------------

        st.subheader(
            "Processing Summary"
        )


        col1, col2, col3, col4 = st.columns(4)


        col1.metric(
            "Total SO Files",
            len(so_folder)
        )


        col2.metric(
            "Target Rows Starting With 4",
            f"{total_target_rows:,}"
        )


        col3.metric(
            "Unique Codes Starting With 4",
            f"{len(all_target_codes):,}"
        )


        col4.metric(
            "Actual Updated Rows",
            f"{total_updated_rows:,}"
        )


        # --------------------------------------------------
        # File Details
        # --------------------------------------------------

        st.subheader(
            "Files Analysis"
        )


        result_df = pd.DataFrame(
            file_results
        )


        st.dataframe(
            result_df,
            use_container_width=True,
            hide_index=True
        )


        # --------------------------------------------------
        # Show Target Codes
        # --------------------------------------------------

        with st.expander(
            "Show All Unique Link Codes Starting With 4"
        ):

            if all_target_codes:

                target_df = pd.DataFrame(
                    sorted(all_target_codes),
                    columns=[
                        "Target Link Code"
                    ]
                )


                # Show whether target exists in PPL
                target_df["Found in PPL"] = (
                    target_df[
                        "Target Link Code"
                    ].isin(lookup)
                )


                # Show replacement RETC code
                target_df["RETC Code"] = (
                    target_df[
                        "Target Link Code"
                    ].map(lookup)
                )


                st.dataframe(
                    target_df,
                    use_container_width=True,
                    hide_index=True
                )

            else:

                st.info(
                    "No Link Codes starting with 4 were found."
                )


        # --------------------------------------------------
        # Download
        # --------------------------------------------------

        st.divider()

        st.subheader(
            "Download Updated Files"
        )


        st.download_button(
            label="Download Updated SO Files",
            data=zip_buffer.getvalue(),
            file_name="Updated_SO_Files.zip",
            mime="application/zip",
            type="primary"
        )