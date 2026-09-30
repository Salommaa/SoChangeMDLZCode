import pandas as pd
import streamlit as st
import os
import zipfile
import io

# -----------------------------------------
# Title
# -----------------------------------------
st.title("SO Handling Tool")


# -----------------------------------------
# Read PPL
# -----------------------------------------
ppl_file = st.file_uploader(
    "Upload The PPL file as Excel",
    type=["xlsx", "xls"]
)

if ppl_file is not None:
    ppl_data = pd.read_excel(ppl_file)
    st.success("PPL file uploaded successfully!")


# -----------------------------------------
# Read SO folder
# -----------------------------------------
so_folder = st.file_uploader(
    "Upload SO Folder",
    type=["csv"],
    accept_multiple_files="directory"
)

if so_folder:
    st.success(f"{len(so_folder)} SO files uploaded successfully!")

    # Show uploaded files
    with st.expander("Show uploaded SO files"):
        for file in so_folder:
            st.write(file.name)


# -----------------------------------------
# Proceed Button
# -----------------------------------------
if ppl_file is not None and so_folder:

    proceed = st.button(
        "Proceed",
        type="primary"
    )

    if proceed:

        # -----------------------------------------
        # Create lookup:
        # MDLZ code -> RETC code
        # -----------------------------------------
        lookup = dict(zip(
            ppl_data["MDLZ code"].astype(str).str.strip(),
            ppl_data["RETC code"].astype(str).str.strip()
        ))

        total_count = 0

        # This will contain the updated/original files
        zip_buffer = io.BytesIO()

        # Store analysis per file
        file_results = []

        # -----------------------------------------
        # Create ZIP
        # -----------------------------------------
        with zipfile.ZipFile(
            zip_buffer,
            "w",
            zipfile.ZIP_DEFLATED
        ) as zip_file:

            # -----------------------------------------
            # Process SO files
            # -----------------------------------------
            for file in so_folder:

                try:

                    # Read uploaded CSV
                    df = pd.read_csv(
                        file,
                        low_memory=False
                    )

                    # ---------------------------------
                    # If no Link Code:
                    # don't change the file
                    # but still add it to download
                    # ---------------------------------
                    if "Link Code" not in df.columns:

                        csv_data = df.to_csv(
                            index=False
                        ).encode("utf-8-sig")

                        zip_file.writestr(
                            file.name,
                            csv_data
                        )

                        file_results.append({
                            "File": file.name,
                            "Replacements": 0,
                            "Status": "No Link Code column"
                        })

                        continue


                    # ---------------------------------
                    # Clean Link Code
                    # ---------------------------------
                    df["Link Code"] = (
                        df["Link Code"]
                        .astype(str)
                        .str.strip()
                    )


                    # ---------------------------------
                    # YOUR TARGET LOGIC
                    # Find Link Codes starting with 4
                    # ---------------------------------
                    target_codes = set(
                        df.loc[
                            df["Link Code"].str.startswith(
                                "4",
                                na=False
                            ),
                            "Link Code"
                        ]
                    )


                    # ---------------------------------
                    # Your mask logic
                    # ---------------------------------
                    mask = df["Link Code"].isin(
                        target_codes
                    )


                    # ---------------------------------
                    # Count
                    # ---------------------------------
                    file_count = mask.nunique()
                    total_count += file_count


                    # ---------------------------------
                    # Replace from PPL
                    # ---------------------------------
                    df.loc[
                        mask,
                        "Link Code"
                    ] = df.loc[
                        mask,
                        "Link Code"
                    ].map(
                        lambda x: lookup.get(x, x)
                    )


                    # ---------------------------------
                    # Add file to ZIP
                    #
                    # IMPORTANT:
                    # This happens even when
                    # file_count = 0
                    # ---------------------------------
                    csv_data = df.to_csv(
                        index=False
                    ).encode("utf-8-sig")

                    zip_file.writestr(
                        file.name,
                        csv_data
                    )


                    # ---------------------------------
                    # Analysis
                    # ---------------------------------
                    file_results.append({
                        "File": file.name,
                        "Replacements": file_count,
                        "Status": (
                            "Updated"
                            if file_count > 0
                            else "No Update"
                        )
                    })


                except Exception as e:

                    # ---------------------------------
                    # If error:
                    # keep original uploaded file
                    # ---------------------------------
                    file.seek(0)

                    zip_file.writestr(
                        file.name,
                        file.read()
                    )

                    file_results.append({
                        "File": file.name,
                        "Replacements": 0,
                        "Status": f"Error: {e}"
                    })


        # -----------------------------------------
        # Finish ZIP
        # -----------------------------------------
        zip_buffer.seek(0)


        # -----------------------------------------
        # Show results
        # -----------------------------------------
        st.success("Processing completed successfully!")


        st.subheader("Processing Summary")

        col1, col2 = st.columns(2)

        col1.metric(
            "Total SO Files",
            len(so_folder)
        )

        col2.metric(
            "Total Codes Starting With 4",
            total_count
        )


        # -----------------------------------------
        # File analysis
        # -----------------------------------------
        result_df = pd.DataFrame(file_results)

        st.subheader("Files")

        st.dataframe(
            result_df,
            use_container_width=True,
            hide_index=True
        )


        # -----------------------------------------
        # Download button
        # -----------------------------------------
        st.download_button(
            label="Download Updated SO Files",
            data=zip_buffer.getvalue(),
            file_name="Updated_SO_Files.zip",
            mime="application/zip",
            type="primary"
        )
